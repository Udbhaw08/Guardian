"""
mcp_server/tools/scan_image_url_tool.py
-----------------------------------------
MCP tool handler for the "scan_image_url" tool.

This tool solves the fundamental ChatGPT MCP limitation:
  ChatGPT cannot pass binary image bytes to MCP tools.
  BUT ChatGPT CAN provide a URL to an uploaded image.

Pipeline:
  1. Receive the image URL from ChatGPT.
  2. Download the image bytes from the URL.
  3. Run our full OCR + ML pipeline (scan_image) on the bytes.
  4. Return BLOCK / WARN_CONFIRM / ALLOW decision.

ARCHITECTURAL CONSTRAINT: No detection logic here — delegate to document_utils/.
"""

from __future__ import annotations

import io
import urllib.request

from detectors.document_utils.image_prompt_injection import scan_image
from mcp_server.tools.scan_document_tool import _build_human_message
from audit.logger import _logger as logger


async def handle_scan_image_url(image_url: str, filename: str = "uploaded_image.png") -> dict:
    """
    Download an image from `image_url` and scan it for prompt injection.

    Args:
        image_url: The URL of the uploaded image (provided by ChatGPT).
        filename:  The original filename (optional, used for display).

    Returns:
        Standard security gateway response dict with decision, reason, etc.
    """
    logger.info("scan_image_url_called", image_url=image_url, filename=filename)
    
    # ── 1. Download the image ─────────────────────────────────────────────────
    try:
        req = urllib.request.Request(
            image_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            image_bytes = resp.read()
        logger.info("image_downloaded", bytes=len(image_bytes))
    except Exception as exc:
        logger.error("image_download_failed", error=str(exc))
        resp = {
            "decision":      "WARN_CONFIRM",
            "matched_types": ["download_error"],
            "reason":        f"Could not download image for scanning: {exc}. Cannot verify image safety.",
            "match_count":   0,
            "confidence":    0.0,
            "severity":      "medium",
            "stealth_flags": [],
            "human_message": (
                f"⚠️ **Security Warning** — The image `{filename}` could not be downloaded for scanning.\n\n"
                f"Error: `{exc}`\n\nPlease proceed with caution."
            ),
        }
        
        try:
            from api import db
            db.insert_document_scan(resp, text_length=0, client_name="mcp_server")
        except Exception as db_exc:
            logger.error("db_insert_failed", error=str(db_exc))
            
        return resp

    # ── 2. Run our OCR + ML pipeline ─────────────────────────────────────────
    result = scan_image(image_bytes)

    # ── 3. Build response ─────────────────────────────────────────────────────
    matched_types = [result.detector_name] if result.decision != "ALLOW" else []
    match_count = 1 if result.decision != "ALLOW" else 0

    resp = {
        "decision":      result.decision,
        "matched_types": matched_types,
        "reason":        result.reason,
        "match_count":   match_count,
        "confidence":    round(result.confidence, 4),
        "severity":      result.severity,
        "stealth_flags": result.stealth_flags,
        "human_message": _build_human_message(result, filename),
    }

    try:
        from api import db
        db.insert_document_scan(resp, text_length=len(image_bytes), client_name="mcp_server")
    except Exception as db_exc:
        logger.error("db_insert_failed", error=str(db_exc))

    return resp
