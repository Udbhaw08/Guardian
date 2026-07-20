"""
audit/logger.py
---------------
Structured JSON audit logging for scan events.

SECURITY INVARIANT: Raw sensitive values are NEVER logged.
Only masked values (DetectorMatch.masked_value) and span offsets are written.

Log output goes to stdout — Render, Heroku, and similar PaaS platforms
capture stdout as their log stream.

ARCHITECTURAL CONSTRAINT: No MCP, SSE, OAuth, or Starlette types here.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from core.models import DetectorMatch, PolicyDecision


# ── Structlog configuration ────────────────────────────────────────────────────

def _add_log_level(logger: Any, method: str, event_dict: EventDict) -> EventDict:  # noqa: ARG001
    event_dict["level"] = method.upper()
    return event_dict


def _configure_structlog() -> None:
    """Configure structlog for JSON output to stdout (or stderr in stdio mode)."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # In MCP stdio mode, stdout is strictly reserved for JSON-RPC messages.
    # Any logging to stdout breaks the MCP protocol and crashes Claude Desktop.
    use_stderr = (
        os.getenv("LOG_STREAM", "").lower() == "stderr"
        or os.getenv("MCP_STDIO", "").lower() == "true"
        or (bool(sys.argv) and any("run_stdio" in arg for arg in sys.argv))
    )
    target_stream = sys.stderr if use_stderr else sys.stdout

    logging.basicConfig(
        format="%(message)s",
        stream=target_stream,
        level=getattr(logging, log_level, logging.INFO),
    )

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        _add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Use pretty console renderer for local development instead of JSON
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=True, exception_formatter=structlog.dev.rich_traceback),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(target_stream)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, log_level, logging.INFO))


# Configure once at module import time
_configure_structlog()

_logger = structlog.get_logger("audit")


# ── Redaction helper ───────────────────────────────────────────────────────────

def mask_text_preview(text: str, max_chars: int = 30) -> str:
    """
    Produce a safe, non-sensitive preview of the scanned text for log context.

    We log only the character count and a short prefix/suffix to help
    identify the request without exposing the full text.
    Example: "Hello, my password is..." → "Hello, my pa...{42 chars total}"
    """
    total = len(text)
    if total <= max_chars:
        # Still mask potential sensitive content by replacing with length only
        return f"[{total} chars]"
    return f"[{total} chars]"


# ── Audit log functions ────────────────────────────────────────────────────────

def log_scan(
    text: str,
    matches: list[DetectorMatch],
    decision: PolicyDecision,
    request_id: str | None = None,
) -> None:
    """
    Emit a structured audit log entry for one scan_prompt() invocation.

    What IS logged:
    - Decision (ALLOW / WARN_CONFIRM / BLOCK)
    - Detector names and match types that fired
    - Masked values and span offsets (character positions only)
    - Text length (not content)
    - Request ID if provided

    What is NEVER logged:
    - Raw sensitive values (raw API keys, CC numbers, passwords, etc.)
    - Full text content
    """
    safe_matches = [
        {
            "detector": m.detector_name,
            "match_type": m.match_type,
            "severity": m.severity,
            "masked_value": m.masked_value,
            "span": list(m.span),
        }
        for m in matches
    ]

    log_entry: dict[str, Any] = {
        "event": "scan_completed",
        "decision": decision.action,
        "reason": decision.reason,
        "highest_severity": decision.highest_severity,
        "match_count": len(matches),
        "matches": safe_matches,
        "text_length": len(text),
        # We intentionally do NOT log text_preview here
    }

    if request_id:
        log_entry["request_id"] = request_id

    if decision.action == "BLOCK":
        _logger.warning(**log_entry)
    elif decision.action == "WARN_CONFIRM":
        _logger.info(**log_entry)
    else:
        _logger.info(**log_entry)


def log_error(message: str, exc: Exception | None = None, **context: Any) -> None:
    """Log an error with optional exception details (no sensitive data)."""
    _logger.error("scan_error", message=message, error=str(exc) if exc else None, **context)


def log_pipeline_stage(stage: str, request_id: str | None = None, **kwargs: Any) -> None:
    """
    Log a step in the multi-stage detection pipeline (e.g., prompt_injection).
    Emits at DEBUG level by default so it doesn't clutter normal logs, unless
    specifically debugging.
    """
    log_entry = {"event": "pipeline_stage", "stage": stage}
    if request_id:
        log_entry["request_id"] = request_id
    log_entry.update(kwargs)
    _logger.debug(**log_entry)

