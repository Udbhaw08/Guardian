"""
api/
----
Thin REST layer for the Guardian dashboard frontend.

This package is a *transport adapter* — same role as mcp_server/, but speaking
plain JSON/HTTP + CORS to a browser instead of MCP JSON-RPC. It reuses the
existing tool handlers (mcp_server/tools/*) and the pure core/ + policy/ layers;
it adds NO detection or policy logic of its own.

The pure layers (core/, detectors/, policy/, audit/) still never import anything
from here — the dependency arrow points inward only.
"""
