"""
core/scanner.py
---------------
The single protocol-agnostic entrypoint for the detection pipeline.

PUBLIC API:
    scan_prompt(text: str) -> ScanResult

ARCHITECTURAL CONSTRAINTS (enforced):
- No imports from mcp_server/, mcp, starlette, uvicorn, or any transport layer.
- No imports of auth types.
- No I/O except via audit.logger (stdout only).
- Detectors are discovered dynamically — no explicit detector imports here.
  Adding a new detector = add a file in detectors/ with @register(). Done.
"""

from __future__ import annotations

from datetime import datetime, timezone

from audit.logger import log_scan
from core.models import ScanResult
from detectors.registry import DETECTOR_REGISTRY, load_all_detectors
from policy.engine import policy_engine

# ── Ensure detectors are registered when this module is first imported ─────────
# load_all_detectors() is idempotent — safe to call multiple times.
load_all_detectors()


def scan_prompt(text: str, request_id: str | None = None) -> ScanResult:
    """
    Scan *text* for sensitive data and return a structured result.

    This function is the single integration point for the MCP tool handler.
    It orchestrates:
        1. All registered detectors (auto-discovered via registry)
        2. Policy engine (YAML-driven decision aggregation)
        3. Audit logging (structured JSON, no raw values)

    Args:
        text:        The raw input text to scan (prompt, message, etc.)
        request_id:  Optional correlation ID for audit logs (e.g. MCP session UUID).

    Returns:
        ScanResult with decision, masked matches, reason, and timestamp.

    Notes:
        - Raw sensitive values are never included in the return value.
        - The function is synchronous and has no hidden network or DB calls.
        - Thread-safe — all mutable state is local to each call.
    """
    # 1. Run all registered detectors
    all_matches = []
    for detector in DETECTOR_REGISTRY.values():
        try:
            matches = detector.detect(text)
            all_matches.extend(matches)
        except Exception as exc:  # noqa: BLE001
            # Detector failures are isolated — a broken detector doesn't
            # prevent others from running.
            from audit.logger import log_error
            log_error(
                f"Detector '{detector.name}' raised an unexpected error.",
                exc=exc,
                detector=detector.name,
            )

    # 2. Aggregate matches into a policy decision
    decision = policy_engine.decide(all_matches)

    # 3. Emit audit log (no raw values, only masked)
    log_scan(text, all_matches, decision, request_id=request_id)

    # 4. Return structured result — MCP tool handler will translate this
    return ScanResult(
        decision=decision.action,
        matches=all_matches,
        reason=decision.reason,
        scanned_at=datetime.now(tz=timezone.utc),
    )
