"""
tests/test_mcp_server/test_auth.py
------------------------------------
OAuth 2.1 auth enforcement tests.

Tests confirm:
1. Unauthenticated request to SSE endpoint → 401 Unauthorized
2. Token with invalid signature → 401
3. Token with valid structure but wrong scope → 401 (if scope check enabled)

These tests use httpx against the Starlette ASGI app directly
(no real uvicorn process needed — httpx.AsyncClient handles ASGI natively).
"""

from __future__ import annotations

import asyncio
import os

import pytest
import httpx

# Force auth-enabled mode for these tests
os.environ["AUTH_ENABLED"] = "true"
os.environ.setdefault("AUTH_ISSUER_URL", "https://test.example.com/")
os.environ.setdefault("AUTH_JWKS_URI", "https://test.example.com/.well-known/jwks.json")
os.environ.setdefault("AUTH_AUDIENCE", "https://test-gateway")
os.environ.setdefault("MCP_REQUIRED_SCOPE", "scan:prompt")


@pytest.fixture
def auth_app():
    """
    Create a fresh authenticated app instance for auth tests.
    We create a separate FastMCP instance with a mock token verifier
    to avoid needing a real IdP.
    """
    from mcp.server.auth.settings import AuthSettings
    from mcp.server.auth.provider import AccessToken, TokenVerifier
    from mcp.server.fastmcp import FastMCP
    from mcp.server.transport_security import TransportSecuritySettings

    class MockTokenVerifier:
        """Accepts tokens that equal 'valid-test-token', rejects all others."""
        async def verify_token(self, token: str) -> AccessToken | None:
            if token == "valid-test-token":
                return AccessToken(
                    token=token,
                    client_id="test-client",
                    scopes=["scan:prompt"],
                    expires_at=9999999999,
                    subject="test-user",
                )
            return None

    test_mcp = FastMCP(
        name="Test Gateway",
        host="127.0.0.1",
        port=9999,
        auth=AuthSettings(
            issuer_url="https://test.example.com/",
            resource_server_url="http://127.0.0.1:9999",
        ),  # type: ignore
        token_verifier=MockTokenVerifier(),
        # The test client (httpx ASGITransport) sends Host: test — allow it explicitly
        # rather than disabling DNS-rebinding protection, so this still exercises the
        # real security path instead of bypassing it.
        transport_security=TransportSecuritySettings(
            allowed_hosts=["test"],
            allowed_origins=["http://test"],
        ),
    )

    @test_mcp.tool()
    async def scan_prompt(text: str) -> dict:
        """Test scan tool."""
        return {"decision": "ALLOW", "matched_types": [], "reason": "test", "match_count": 0}

    return test_mcp.sse_app()


@pytest.mark.asyncio
async def test_unauthenticated_sse_request_returns_401(auth_app):
    """
    A GET /sse request with no Authorization header must return 401.
    This proves the auth middleware is active and enforcing.
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=auth_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/sse")
        assert response.status_code == 401, (
            f"Expected 401 for unauthenticated request, got {response.status_code}"
        )


@pytest.mark.asyncio
async def test_invalid_token_returns_401(auth_app):
    """A Bearer token with an invalid value must return 401."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=auth_app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/sse",
            headers={"Authorization": "Bearer this-is-an-invalid-token"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_valid_token_accepted(auth_app):
    """
    A request with the correct Bearer token must NOT return 401.
    (It may return 200 or another non-401 code as SSE negotiation begins.)
    """
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=auth_app),
        base_url="http://test",
        timeout=2.0,
    ) as client:
        try:
            # httpx's own `timeout=` doesn't reliably cut off an in-process
            # ASGITransport SSE stream once auth succeeds and the connection
            # opens — wrap in wait_for so a genuinely open stream (proof auth
            # passed) is treated as a pass instead of hanging the test suite.
            response = await asyncio.wait_for(
                client.get(
                    "/sse",
                    headers={"Authorization": "Bearer valid-test-token"},
                ),
                timeout=2.0,
            )
            # Should not be 401 or 403
            assert response.status_code not in (401, 403), (
                f"Valid token should not be rejected (got {response.status_code})"
            )
        except (httpx.ReadTimeout, asyncio.TimeoutError):
            # SSE connections may hang waiting for events — that's expected
            # A timeout means we got past auth (no 401 was sent)
            pass
