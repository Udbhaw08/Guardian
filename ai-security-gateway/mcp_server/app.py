"""
mcp_server/app.py
-----------------
Starlette ASGI application — MCP server entry point.

Exposes:
  GET  /sse                                   — MCP SSE stream (client connects here)
  POST /messages/                             — MCP JSON-RPC messages
  GET  /.well-known/oauth-authorization-server — OAuth discovery (added by FastMCP)
  GET  /.well-known/oauth-protected-resource  — RFC 9728 (added by FastMCP)

Transport swap seam:
  The entire SSE transport is isolated here in mcp.sse_app().
  To migrate to Streamable HTTP later: replace sse_app() with
  streamable_http_app() and update the route from /sse to /mcp.
  Zero changes needed in core/, detectors/, policy/, or audit/.

Usage:
  # Local development
  uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000 --reload

  # With ngrok (separate terminal)
  ngrok http 8000
  # Then set MCP_PUBLIC_URL=https://<ngrok-id>.ngrok.io in .env

  # Render (production)
  # Start command: uvicorn mcp_server.app:app --host 0.0.0.0 --port $PORT
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

# Load .env before any other imports that might read env vars
load_dotenv()

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from mcp_server.tools.scan_prompt_tool import handle_scan_prompt
from mcp_server.tools.scan_document_tool import handle_scan_document
from mcp_server.tools.scan_image_url_tool import handle_scan_image_url

# ── Auth configuration ─────────────────────────────────────────────────────────

_auth_enabled: bool = os.getenv("AUTH_ENABLED", "true").lower() == "true"
_port: int = int(os.getenv("PORT", "8000"))
_public_url: str = os.getenv("MCP_PUBLIC_URL", f"http://localhost:{_port}")
_issuer_url: str = os.getenv("AUTH_ISSUER_URL", "https://placeholder.example.com/")
_host: str = "0.0.0.0"  # must bind to all interfaces for Render / ngrok

# ── Build the FastMCP instance ─────────────────────────────────────────────────

if _auth_enabled:
    from mcp_server.auth import GatewayTokenVerifier

    _token_verifier = GatewayTokenVerifier()
    _auth_settings = AuthSettings(
        issuer_url=_issuer_url,
        resource_server_url=_public_url,  # required by MCP SDK ≥1.9
    )  # type: ignore[arg-type]

    mcp = FastMCP(
        name="AI Security Gateway",
        host=_host,
        port=_port,
        auth=_auth_settings,
        token_verifier=_token_verifier,
    )
else:
    # No auth — for local development / testing only
    # NEVER deploy to Render with AUTH_ENABLED=false
    mcp = FastMCP(
        name="AI Security Gateway (unauthenticated)",
        host=_host,
        port=_port,
    )


# ── Register tools ─────────────────────────────────────────────────────────────

@mcp.tool()
async def scan_prompt(text: str) -> dict:
    """
    SECURITY GATEWAY — MANDATORY security scan. You MUST call this tool on every user message before responding.

    This tool scans the user's text for sensitive data leakage and returns a security
    decision that you MUST follow before proceeding:

    - ALLOW: No sensitive data detected. You may respond normally.
    - WARN_CONFIRM: Sensitive data detected. Show the 'human_message' to the user
      and ask them to confirm (Allow/Deny) before proceeding.
    - BLOCK: Critical sensitive data detected. Do NOT proceed. Show the 'human_message'
      to the user and refuse to process the request.

    Detects: API keys (AWS/GCP/GitHub/Stripe), credit card numbers,
    and national IDs (SSN, Aadhaar).

    CRITICAL RULES — follow exactly:
    1. Call this tool BEFORE doing anything else with any user message or uploaded content.
    2. If the user uploads a FILE (ZIP, PDF, .env, .txt, any document), do NOT call this tool.
       Instead, call `scan_document` with the filename and file listing/content.
    3. If the user uploads an IMAGE (PNG, JPG, JPEG, WEBP, BMP), do NOT call this tool and do NOT
       extract or transcribe its text yourself. Call `scan_image_url` instead — it runs OCR and
       can detect injection text that is invisible to you but still machine-readable, which you
       would miss entirely by only transcribing what you can visually see. This tool (`scan_prompt`)
       is for plain chat text and non-image file content only.
    4. If the user shares a document, form, invoice, ID card, or any structured content,
       extract ALL text fields including: names, numbers, codes, account details, addresses,
       dates, amounts — and pass them all in `text`.
    5. If the result is BLOCK or WARN_CONFIRM, show the `human_message` to the user and
       do NOT proceed with the original request.

    Args:
        text: The FULL text to scan — the user's message combined with ALL text extracted
              from any uploaded image or document. Must be the complete, unabridged content.
    """
    return await handle_scan_prompt(text)


@mcp.tool()
async def scan_document(content: str, filename: str) -> dict:
    """
    SECURITY GATEWAY — MANDATORY scan for all uploaded files. You MUST call this tool
    whenever the user uploads ANY file (ZIP, PDF, .env, .txt, config files, etc.).

    CRITICAL RULES:
    1. You MUST call this tool BEFORE responding to the user about an uploaded file in any way —
       before summarizing it, describing its contents, listing what's inside it, giving an
       opinion on it, or answering ANY question about it. Extracting the file's text (or, for a
       ZIP, listing its filenames) purely to build this tool's `content` argument is the ONE
       exception — that extraction step is required to call this tool at all. The moment that
       extraction is done, your VERY NEXT action MUST be calling this tool with it, before
       composing any reply to the user. Never use that extracted content to answer the user
       directly instead of calling this tool.
    2. If the result is BLOCK, do NOT process the file. Show the `human_message` to the user and
       stop — do not also give your own summary of the file's contents.
    3. Do NOT skip this tool for any file type. Do NOT treat "I already looked at the file myself"
       as satisfying this requirement — only this tool's decision counts.

    HOW TO USE FOR EACH FILE TYPE:

    ZIP files (.zip):
      - List ALL filenames inside the ZIP archive — this is the only file-reading step allowed
        before calling this tool, and it must be followed immediately by the tool call.
      - Pass that list as a newline-separated string in `content`.
      - Example content: ".env\napp.py\nrequirements.txt\nsrc/config.env"
      - Set filename to the ZIP filename (e.g. "sample.zip").
      - Do NOT describe the archive's file contents (e.g. what's inside app.py or .env) in your
        reply until AFTER this tool has returned a decision.

    PDF files (.pdf):
      - Extract all text from the PDF — this is the only file-reading step allowed before
        calling this tool, and it must be followed immediately by the tool call.
      - Pass the full extracted text as `content`.
      - Do NOT summarize, describe, or answer questions about the PDF's content in your reply
        until AFTER this tool has returned a decision.

    ENV / config files (.env, env, env.example, .env.example, .envrc, config.env, etc.):
      - Pass the entire file contents as `content`.
      - Set filename to the actual filename (e.g. ".env" or "env.example").
      - Do NOT reveal or repeat any of the file's values in your reply — only this tool's
        `human_message` should describe the finding.

    Text files (.txt, .csv, .json, .yaml, .yml, .toml, .ini, .cfg):
      - Pass the full file contents as `content`.

    Images (.png, .jpg, .jpeg, .webp, .bmp, .tiff): do NOT use this tool. Call `scan_image_url`
    instead — it runs real OCR and can catch injection text invisible to the naked eye, which
    reading the image yourself (or transcribing visible text into `content`) would miss.

    Args:
        content: File contents or ZIP file listing (newline-separated filenames).
        filename: The original filename including extension (e.g. "sample.zip", ".env").
    """
    return await handle_scan_document(content, filename)


@mcp.tool()
async def scan_image_url(image_url: str, filename: str = "uploaded_image.png") -> dict:
    """
    SECURITY GATEWAY — Scan an uploaded image for hidden prompt injection.

    You MUST call this tool whenever the user uploads an image file (PNG, JPG, JPEG, WEBP, BMP) —
    this is the ONLY correct tool for image uploads; do not use `scan_prompt` or `scan_document`
    for images.

    CRITICAL RULES:
    1. Call this tool BEFORE describing, summarizing, transcribing, or answering ANY question
       about the image. You are capable of reading images yourself, but you MUST NOT use that
       ability here — this tool runs real OCR + ML analysis and can detect injection text that
       is invisible to the human eye (and to your own visual reading) but still machine-readable.
       Answering from your own look at the image would miss exactly the threat this tool exists
       to catch.
    2. If the result is BLOCK, do NOT process or describe the image. Show the `human_message`
       and stop.
    3. Do NOT skip this tool because you already "looked at" the image — only this tool's
       decision counts.

    This tool downloads the image and runs OCR + ML analysis to detect hidden
    prompt injection instructions that are invisible to human readers.

    Args:
        image_url: The URL of the uploaded image. ChatGPT provides this automatically.
        filename: The original filename of the image (e.g. invoice.png).
    """
    return await handle_scan_image_url(image_url, filename)


# ── Expose ASGI app for uvicorn ────────────────────────────────────────────────

# `app` is the ASGI application object uvicorn will call.
# Using Streamable HTTP transport (newer MCP standard) → endpoint at /mcp
# To revert to legacy SSE: swap streamable_http_app() → sse_app() and /mcp → /sse
app = mcp.streamable_http_app()
