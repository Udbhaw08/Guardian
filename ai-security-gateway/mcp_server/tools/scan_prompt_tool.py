"""
mcp_server/tools/scan_prompt_tool.py
-------------------------------------
MCP tool handler for the "scan-prompt" tool.

Responsibility: Translate between MCP calling conventions and core.scanner.
  - Receive validated input from FastMCP (text: str)
  - Call core.scanner.scan_prompt() — the ONLY coupling to the core layer
  - Translate ScanResult into a plain dict that FastMCP serialises into
    an MCP tool response.

HARD CONSTRAINTS:
  - No raw sensitive values in the returned dict (matched_types only, not values).
  - No detection or policy logic here — delegate everything to core.scanner.
  - No auth logic here — auth is handled by FastMCP middleware in app.py.
"""

from __future__ import annotations

from core.scanner import scan_prompt as _core_scan

# ── Policy display metadata — maps detector name → human-readable label/icon ──
_POLICY_META: dict[str, tuple[str, str]] = {
    "api_key":          ("🔑", "Credentials / API Key"),
    "credit_card":      ("💳", "Payment Data / Credit Card"),
    "national_id":      ("🪪", "National Identifier (PAN / Aadhaar / SSN)"),
    "financial":        ("🏦", "Financial Info (Bank A/C / IFSC / GSTIN)"),
    "prompt_injection": ("🚨", "Prompt Injection / Jailbreak"),
    "env_file":         ("📄", "Environment / Secrets File (.env)"),
    "zip_env_leak":     ("🗜️", "ZIP Archive Contains Secrets File"),
}

_SEVERITY_BAR: dict[str, str] = {
    "critical": "🔴 CRITICAL",
    "high":     "🟠 HIGH",
    "medium":   "🟡 MEDIUM",
    "low":      "🟢 LOW",
}


def _build_human_message(
    decision: str,
    matched_types: list[str],
    reason: str,
    match_count: int,
    matches: list | None = None,
) -> str:
    """
    Build a rich markdown-formatted message that ChatGPT renders inside its
    native tool-call UI (the popup panel).
    """
    if decision == "ALLOW":
        return (
            "## ✅ AI Security Gateway — Clear\n\n"
            "> No sensitive data or threats detected in your content.\n\n"
            "| Status | Details |\n"
            "|--------|--------|\n"
            "| 🟢 Decision | **ALLOW** |\n"
            "| 🔍 Threats Found | None |\n"
            "| 🛡️ Policy | All checks passed |\n\n"
            "_Your content is safe to process._"
        )

    # Build a detailed findings table
    findings_rows: list[str] = []
    match_type_counts: dict[str, list[str]] = {}

    if matches:
        for m in matches:
            sev_badge = _SEVERITY_BAR.get(m.severity, m.severity.upper())
            _, label = _POLICY_META.get(m.detector_name, ("⚠️", m.detector_name.replace("_", " ").title()))
            key = f"{label}|{sev_badge}"
            if key not in match_type_counts:
                match_type_counts[key] = []
            match_type_counts[key].append(m.match_type.replace("_", " "))

        for key, types in match_type_counts.items():
            label, sev_badge = key.split("|", 1)
            type_str = ", ".join(dict.fromkeys(types))  # deduplicate
            findings_rows.append(f"| {label} | {sev_badge} | {type_str} |")
    else:
        for dtype in matched_types:
            _, label = _POLICY_META.get(dtype, ("⚠️", dtype.replace("_", " ").title()))
            findings_rows.append(f"| {label} | 🟠 HIGH | — |")

    findings_table = (
        "| Category | Severity | Type |\n"
        "|----------|----------|------|\n"
        + "\n".join(findings_rows)
    )

    if decision == "WARN_CONFIRM":
        return (
            "## 🛡️ AI Security Gateway — Sensitive Data Detected\n\n"
            f"> ⚠️ **{match_count} sensitive item(s) found** in your content. Review before proceeding.\n\n"
            "### 📋 Security Findings\n\n"
            f"{findings_table}\n\n"
            "---\n\n"
            "### ⚠️ What this means\n"
            "Sharing this content with the AI may expose private or sensitive information "
            "to external systems. You are in control.\n\n"
            "**Reply with `Allow` to proceed** or **`Deny` to cancel.**"
        )

    # BLOCK
    return (
        "## 🚫 AI Security Gateway — Request BLOCKED\n\n"
        f"> 🔴 **This request has been blocked** — {match_count} critical threat(s) detected.\n\n"
        "### 📋 Security Findings\n\n"
        f"{findings_table}\n\n"
        "---\n\n"
        "### ❌ Why was this blocked?\n"
        f"{reason}\n\n"
        "Your request **cannot be processed**. Please remove the sensitive data "
        "and try again, or contact your security administrator.\n\n"
        "_Powered by AI Security Gateway — FYP Project_"
    )


async def handle_scan_prompt(text: str, request_id: str | None = None) -> dict:
    """
    Handle a "scan-prompt" MCP tool call.

    Args:
        text:        The text submitted by the MCP client to be scanned.
        request_id:  Optional correlation ID forwarded to audit logs.

    Returns:
        A plain dict suitable for MCP tool response serialisation:
        {
            "decision":      "ALLOW" | "WARN_CONFIRM" | "BLOCK",
            "matched_types": ["api_key", "credit_card", ...],
            "reason":        "Human-readable explanation.",
            "match_count":   3,
            "human_message": "Markdown-formatted message for ChatGPT popup.",
        }

        NOTE: No raw sensitive values are included. Only detector type names.
    """
    # scan_prompt() is synchronous (pure CPU-bound); fine in async context
    import structlog
    log = structlog.get_logger("gateway.scan_prompt")

    log.info("pipeline_start", stage="REQUEST_RECEIVED", text_length=len(text))
    log.info("pipeline_step", stage="SCANNING", detectors="all_registered", text_preview=text[:1000])

    result = _core_scan(text, request_id=request_id)

    matched_types = result.matched_detector_names

    # Build per-detector summary for logging
    detector_summary = {}
    for m in result.matches:
        detector_summary[m.detector_name] = detector_summary.get(m.detector_name, 0) + 1

    if detector_summary:
        detected_str = ", ".join(f"{k}({v})" for k, v in detector_summary.items())
    else:
        detected_str = "None"

    log.info(
        "pipeline_step",
        stage="SCAN_COMPLETE",
        detected=detected_str,
        match_count=len(result.matches),
        decision=result.decision,
    )
    log.info("pipeline_end", stage="RESPONSE_SENT", decision=result.decision)

    # ── 2. Persist to Dashboard Database (non-blocking) ────────────────────────
    try:
        from api import db
        row_id = db.insert_scan(result, text_length=len(text), client_name="mcp_server")
        log.info("db_insert_ok", row_id=row_id)
    except Exception as exc:
        log.error("db_insert_failed", error=repr(exc), exc_info=True)

    return {
        "decision":      result.decision,
        "matched_types": matched_types,
        "reason":        result.reason,
        "match_count":   len(result.matches),
        "human_message": _build_human_message(
            result.decision, matched_types, result.reason, len(result.matches),
            matches=result.matches,
        ),
    }
