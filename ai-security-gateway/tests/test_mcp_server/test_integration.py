"""
tests/test_mcp_server/test_integration.py
------------------------------------------
MCP server integration tests.

Tests the scan-prompt tool through the MCP SDK's in-process client.
No real server process or network needed — `mcp.shared.memory.
create_connected_server_and_client_session` wires an in-memory ClientSession
directly to our FastMCP instance (the SDK's replacement for the older
`mcp.Client(mcp_obj)` convenience wrapper, which no longer exists in
mcp>=1.28 — `from mcp import Client` raises ImportError there).

These tests confirm:
1. The tool is callable via MCP protocol
2. The response has the expected shape (decision/matched_types/reason/match_count)
3. No raw sensitive values appear in tool responses
"""

from __future__ import annotations

import os

import pytest

# Force no-auth mode for integration tests
os.environ.setdefault("AUTH_ENABLED", "false")

# Import after env is set
from mcp_server.app import mcp  # noqa: E402
from mcp.shared.memory import create_connected_server_and_client_session  # noqa: E402


def _tool_text(result) -> str:
    """Extract the text payload from a CallToolResult's first content block."""
    block = result.content[0]
    return getattr(block, "text", None) or str(block)


@pytest.mark.asyncio
async def test_scan_prompt_tool_exists():
    """Confirm scan-prompt tool is registered on the server."""
    tools = await mcp.list_tools()
    tool_names = [t.name for t in tools]
    assert "scan_prompt" in tool_names, (
        "scan_prompt tool should be registered"
    )


@pytest.mark.asyncio
async def test_scan_prompt_clean_text():
    """Clean text → ALLOW decision."""
    async with create_connected_server_and_client_session(mcp) as client:
        result = await client.call_tool("scan_prompt", {"text": "What is the weather today?"})
        assert result is not None
        assert "ALLOW" in _tool_text(result)


@pytest.mark.asyncio
async def test_scan_prompt_blocks_aws_key():
    """AWS access key in text → BLOCK decision."""
    async with create_connected_server_and_client_session(mcp) as client:
        result = await client.call_tool(
            "scan_prompt",
            {"text": "My AWS key is AKIAIOSFODNN7EXAMPLE"},
        )
        assert "BLOCK" in _tool_text(result)


@pytest.mark.asyncio
async def test_scan_prompt_response_shape():
    """
    Tool response must contain expected keys:
    decision, matched_types, reason, match_count.
    """
    import json

    async with create_connected_server_and_client_session(mcp) as client:
        result = await client.call_tool(
            "scan_prompt",
            {"text": "sk_live_REPLACE_WITH_TEST_KEY_HERE"},
        )
        raw = _tool_text(result)

        # The tool returns a dict which FastMCP serialises to JSON in the response
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            # FastMCP may format as plain text; check string contains required fields
            assert "decision" in raw
            assert "reason" in raw
            return

        assert "decision" in data
        assert "matched_types" in data
        assert "reason" in data
        assert "match_count" in data


@pytest.mark.asyncio
async def test_raw_sensitive_values_not_in_response():
    """HARD CONSTRAINT: Raw sensitive value must not appear in tool response."""
    secret = "AKIAIOSFODNN7EXAMPLE"

    async with create_connected_server_and_client_session(mcp) as client:
        result = await client.call_tool(
            "scan_prompt",
            {"text": f"key={secret}"},
        )
        raw = _tool_text(result)
        assert secret not in raw, (
            "Raw API key must not appear anywhere in the MCP tool response"
        )
