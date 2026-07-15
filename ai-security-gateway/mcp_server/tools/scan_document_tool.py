"""
mcp_server/tools/scan_document_tool.py
----------------------------------------
MCP tool handler for the "scan_document" tool.

Responsibility:
  - Accept a base64-encoded file and filename from the MCP client.
  - Auto-detect file type by extension (.pdf, .png, .jpg, .webp, .bmp, .tiff, .zip).
  - Route to the appropriate scanner (PDF, Image, or ZIP pipeline).
  - Translate scan results into a plain dict (same shape as scan_prompt).

HARD CONSTRAINTS:
  - No raw file contents in the returned dict.
  - No detection or policy logic here — delegate to document_utils/.
  - No auth logic here — auth is handled by FastMCP middleware in app.py.
"""

from __future__ import annotations

import base64

from detectors.document_utils.pdf_prompt_injection import scan_pdf, DocumentScanResult
from detectors.document_utils.image_prompt_injection import scan_image
from detectors.document_utils.zip_scanner import scan_zip, ZipScanResult

# ── Supported file extensions ─────────────────────────────────────────────────

_PDF_EXTENSIONS   = frozenset({".pdf"})
_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"})
_ZIP_EXTENSIONS   = frozenset({".zip"})

# ── Policy display metadata ───────────────────────────────────────────────────

_SEVERITY_BAR: dict[str, str] = {
    "critical": "🔴 CRITICAL",
    "high":     "🟠 HIGH",
    "medium":   "🟡 MEDIUM",
    "low":      "🟢 LOW",
}


def _build_human_message(result: DocumentScanResult, filename: str) -> str:
    """Build a markdown-formatted message for the LLM's tool-call UI."""
    severity_label = _SEVERITY_BAR.get(result.severity, result.severity.upper())
    file_type = "PDF" if result.detector_name == "pdf_prompt_injection" else "Image"

    if result.decision == "ALLOW":
        return (
            f"✅ **Security check passed.** No prompt injection detected in `{filename}`. "
            f"The {file_type} is safe to process."
        )

    flags_str = ", ".join(result.stealth_flags) if result.stealth_flags else "none"
    confidence_pct = f"{result.confidence:.0%}" if result.confidence > 0 else "N/A"

    header = (
        "## 🚫 AI Security Gateway — Document Blocked"
        if result.decision == "BLOCK"
        else "## ⚠️ AI Security Gateway — Document Warning"
    )

    body = (
        f"{header}\n\n"
        f"**File:** `{filename}`\n"
        f"**Type:** {file_type}\n"
        f"**Severity:** {severity_label}\n"
        f"**ML Confidence:** {confidence_pct}\n"
        f"**Stealth Flags:** `{flags_str}`\n\n"
        f"**Reason:** {result.reason}\n\n"
        f"---\n"
    )

    if result.decision == "BLOCK":
        body += (
            "This document cannot be processed. It appears to contain hidden prompt injection "
            "instructions that are not visible to human readers but can be extracted by AI systems."
        )
    else:
        body += (
            "This document contains suspicious patterns. "
            "**Do you want to proceed anyway?** Reply with **Allow** or **Deny**."
        )

    return body


def _log_doc_scan(resp: dict, text_length: int) -> None:
    """Helper to safely persist a document/image scan result to the database."""
    try:
        from api import db
        row_id = db.insert_document_scan(resp, text_length=text_length, client_name="mcp_server")
        import structlog
        structlog.get_logger("gateway.scan_document").info("db_insert_ok", row_id=row_id)
    except Exception as exc:
        import structlog
        structlog.get_logger("gateway.scan_document").error(
            "db_insert_failed", error=repr(exc), exc_info=True
        )


def _handle_zip_listing(file_listing: str, filename: str) -> dict:
    """
    Handle ZIP files by scanning their filename listing for sensitive env files.

    ChatGPT cannot pass raw binary bytes to MCP tools, so for ZIP archives
    the tool docstring instructs ChatGPT to pass the newline-separated list
    of all filenames inside the ZIP. This function runs the zip_scanner's
    pattern matching directly on that filename list.
    """
    from detectors.document_utils.zip_scanner import _is_sensitive, ZipScanResult

    # Parse filenames — support newline, comma, or semicolon separators
    raw = file_listing.replace(",", "\n").replace(";", "\n")
    all_files = [
        line.strip().strip("/")
        for line in raw.splitlines()
        if line.strip() and not line.strip().endswith("/")  # skip directory entries
    ]

    sensitive = [f for f in all_files if _is_sensitive(f)]

    if not sensitive:
        resp = {
            "decision":      "ALLOW",
            "matched_types": [],
            "reason":        f"ZIP archive is clean. Scanned {len(all_files)} file(s). No sensitive env files found.",
            "match_count":   0,
            "confidence":    0.0,
            "severity":      "low",
            "stealth_flags": [],
            "human_message": (
                f"ZIP archive `{filename}` is clean. "
                f"Scanned {len(all_files)} file(s). No .env or secret files found."
            ),
        }
        _log_doc_scan(resp, len(file_listing))
        return resp

    root_level = [f for f in sensitive if "/" not in f]
    severity = "critical" if root_level else "high"
    reason = (
        f"{'CRITICAL' if root_level else 'HIGH'}: "
        f"Sensitive env file(s) detected inside ZIP: {sensitive}. "
        f"These files likely contain plaintext secrets (API keys, passwords, tokens). "
        f"Remove them before sharing this archive."
    )
    files_str = ", ".join(f"`{f}`" for f in sensitive)
    human_message = (
        f"## Security Gateway — ZIP Blocked\n\n"
        f"**File:** `{filename}`\n"
        f"**Severity:** {'CRITICAL' if root_level else 'HIGH'}\n"
        f"**Sensitive files found:** {files_str}\n\n"
        f"{reason}"
    )

    resp = {
        "decision":      "BLOCK",
        "matched_types": ["zip_env_leak"],
        "reason":        reason,
        "match_count":   len(sensitive),
        "confidence":    1.0,
        "severity":      severity,
        "stealth_flags": sensitive,
        "human_message": human_message,
    }
    _log_doc_scan(resp, len(file_listing))
    return resp


async def handle_scan_document(file_b64: str, filename: str) -> dict:
    """
    Handle a "scan_document" MCP tool call.

    Args:
        file_b64:  Base64-encoded file contents.
        filename:  Original filename including extension (used for type detection).

    Returns:
        A plain dict:
        {
            "decision":      "ALLOW" | "WARN_CONFIRM" | "BLOCK",
            "matched_types": ["pdf_prompt_injection"] or ["zip_env_leak"],
            "reason":        "Human-readable explanation.",
            "match_count":   1,
            "confidence":    0.94,
            "stealth_flags": ["white_on_white", "tiny_font"],
            "human_message": "Markdown-formatted message for LLM UI.",
        }
    """
    # ── 1. Detect file type from extension first ──────────────────────────────
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # ── 2. ZIP: accept file listing text instead of binary bytes ─────────────
    # ChatGPT cannot pass binary file bytes to MCP tools. For ZIP archives,
    # the tool docstring instructs ChatGPT to pass the newline-separated list
    # of filenames inside the ZIP. We detect this case here and run the
    # zip_scanner on the text listing directly (no base64 decode needed).
    if ext in _ZIP_EXTENSIONS:
        return _handle_zip_listing(file_b64, filename)

    # ── 3. Validate and decode base64 OR handle plaintext ────────────────────
    is_base64 = False
    file_bytes = b""
    try:
        # validate=True rejects non-base64 alphabet (like plain text with spaces)
        file_bytes = base64.b64decode(file_b64, validate=True)
        is_base64 = True
    except Exception:
        # It's not base64. ChatGPT probably extracted the text and passed it directly.
        is_base64 = False

    # ── 4. Detect file type for PDF / Image ───────────────────────────────────
    if not is_base64:
        # Fallback: Treat file_b64 as plain text extracted by the LLM
        extracted_text = file_b64.strip()
        from detectors.document_utils.classifier import classify_text
        from detectors.document_utils.stealth_rules import StealthCheckResult
        from detectors.document_utils.pdf_prompt_injection import _decide
        
        # Split text into lines to prevent a large document from diluting the malicious instruction
        lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
        max_conf = 0.0
        ml_injection = False
        
        # Check the document as a whole first
        ml_inj, ml_conf = classify_text(extracted_text)
        if ml_conf > max_conf:
            max_conf = ml_conf
            ml_injection = ml_inj
            
        # Then check line by line
        for line in lines:
            if len(line) < 10: continue
            linj, lconf = classify_text(line)
            if lconf > max_conf:
                max_conf = lconf
                ml_injection = linj
                
        decision, severity, reason, match_type = _decide(
            ml_injection, max_conf, StealthCheckResult()
        )
        
        if decision != "ALLOW":
            reason = f"[LLM Extraction] {reason}"
            
        result = DocumentScanResult(
            decision=decision,
            severity=severity,
            reason=reason,
            confidence=max_conf,
            stealth_flags=[],
            extracted_text_length=len(extracted_text),
            page_count=1,
            detector_name="image_prompt_injection" if ext in _IMAGE_EXTENSIONS else "pdf_prompt_injection",
            match_type=match_type,
        )
    else:
        # It's actual binary base64
        if ext in _PDF_EXTENSIONS:
            result = scan_pdf(file_bytes)
        elif ext in _IMAGE_EXTENSIONS:
            result = scan_image(file_bytes)
        elif ext in _ZIP_EXTENSIONS:
            zip_result = scan_zip(file_bytes)
            # ZIP has its own result shape — build response directly
            matched_types = [zip_result.detector_name] if zip_result.decision != "ALLOW" else []
            match_count   = len(zip_result.sensitive_files)
            if zip_result.decision == "ALLOW":
                human_msg = (
                    f"ZIP archive `{filename}` is clean. "
                    f"Scanned {zip_result.file_count} file(s). No .env or secret files found."
                )
            else:
                files_str = ", ".join(f"`{f}`" for f in zip_result.sensitive_files)
                human_msg = (
                    f"## Security Gateway — ZIP Blocked\n\n"
                    f"**File:** `{filename}`\n"
                    f"**Sensitive files found:** {files_str}\n\n"
                    f"{zip_result.reason}"
                )
            resp = {
                "decision":      zip_result.decision,
                "matched_types": matched_types,
                "reason":        zip_result.reason,
                "match_count":   match_count,
                "confidence":    1.0 if zip_result.decision == "BLOCK" else 0.0,
                "severity":      zip_result.severity,
                "stealth_flags": zip_result.sensitive_files,
                "human_message": human_msg,
            }
            _log_doc_scan(resp, len(file_bytes))
            return resp
        else:
            resp = {
                "decision":      "BLOCK",
                "matched_types": [],
                "reason":        f"Unsupported file type '{ext}'. Supported: PDF, PNG, JPG, WEBP, BMP, TIFF, ZIP.",
                "match_count":   0,
                "confidence":    0.0,
                "severity":      "high",
                "stealth_flags": [],
                "human_message": (
                    f"Unsupported file type: `{filename}`\n\n"
                    f"Supported formats: PDF, PNG, JPG, WEBP, BMP, TIFF, ZIP."
                ),
            }
            _log_doc_scan(resp, len(file_b64))
            return resp

    # ── 3. Build and return response dict ─────────────────────────────────────
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
    
    # Calculate appropriate text length context
    content_len = len(file_bytes) if is_base64 else len(file_b64)
    _log_doc_scan(resp, content_len)
    return resp
