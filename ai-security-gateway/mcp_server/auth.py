"""
mcp_server/auth.py
------------------
OAuth 2.1 TokenVerifier for the AI Security Gateway.

Mode: Resource Server (simple).
  - Our server validates Bearer tokens issued by an external Authorization Server.
  - We do NOT issue tokens ourselves — that's the IdP's job.
  - Clients (Claude, ChatGPT) authenticate against the external IdP and present
    the resulting Bearer token to our server.

Token validation strategy:
  1. Decode the JWT header to get the key ID (kid).
  2. Fetch the JWKS from AUTH_JWKS_URI (cached with a TTL to avoid hammering the IdP).
  3. Verify the JWT signature, expiry, issuer (iss), and audience (aud).
  4. Optionally check that the token contains MCP_REQUIRED_SCOPE.
  5. Return an AccessToken on success, None on failure (SDK returns 401 to client).

All config is read from environment variables — no hardcoded values.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
import jwt  # PyJWT
from jwt import PyJWKClient, PyJWKClientError

from mcp.server.auth.provider import AccessToken, TokenVerifier


class GatewayTokenVerifier:
    """
    Validates Bearer JWTs against the configured Authorization Server's JWKS.

    Implements the mcp.server.auth.provider.TokenVerifier protocol so that
    FastMCP's BearerAuthBackend can call verify_token() transparently.

    Configuration (all from environment, loaded once at init):
        AUTH_JWKS_URI        — JWKS endpoint URL
        AUTH_ISSUER_URL      — Expected 'iss' claim value
        AUTH_AUDIENCE        — Expected 'aud' claim value
        MCP_REQUIRED_SCOPE   — Required scope in the token (optional check)
    """

    def __init__(self) -> None:
        self._jwks_uri: str = _require_env("AUTH_JWKS_URI")
        self._issuer: str = _require_env("AUTH_ISSUER_URL").rstrip("/")
        self._audience: str = _require_env("AUTH_AUDIENCE")
        self._required_scope: str | None = os.getenv("MCP_REQUIRED_SCOPE")

        # PyJWT's JWKS client handles key caching and rotation automatically
        self._jwks_client = PyJWKClient(
            self._jwks_uri,
            cache_jwk_set=True,
            lifespan=300,  # refresh JWKS every 5 minutes
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        """
        Verify *token* and return an AccessToken if valid, else None.

        FastMCP calls this for every incoming request. Returning None causes
        FastMCP to respond with HTTP 401 Unauthorized automatically.
        """
        try:
            # 1. Fetch the signing key matching this token's 'kid'
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)

            # 2. Verify signature + standard claims
            payload: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["exp", "iat", "iss", "sub"]},
            )

            # 3. Scope check (optional — only if MCP_REQUIRED_SCOPE is set)
            if self._required_scope:
                token_scopes = self._parse_scopes(payload)
                if self._required_scope not in token_scopes:
                    return None  # scope mismatch → 401

            # 4. Build the AccessToken object the SDK expects
            return AccessToken(
                token=token,
                client_id=payload.get("azp") or payload.get("client_id") or "unknown",
                scopes=self._parse_scopes(payload),
                expires_at=int(payload.get("exp", time.time() + 3600)),
                subject=payload.get("sub"),
                claims=payload,
            )

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, PyJWKClientError):
            return None  # invalid token → FastMCP returns 401

    @staticmethod
    def _parse_scopes(payload: dict[str, Any]) -> list[str]:
        """Parse the 'scope' claim from a JWT payload (space-separated string or list)."""
        scope_val = payload.get("scope", "")
        if isinstance(scope_val, list):
            return scope_val
        return scope_val.split() if scope_val else []


def _require_env(name: str) -> str:
    """Read a required env var or raise a clear startup error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            f"Check your .env file (see .env.example for reference)."
        )
    return value
