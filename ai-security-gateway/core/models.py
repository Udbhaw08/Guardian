"""
core/models.py
--------------
Pure Pydantic data contracts for the detection pipeline.

ARCHITECTURAL CONSTRAINT: No MCP, SSE, OAuth, or Starlette types may be
imported here. These models are the shared language between core/, detectors/,
policy/, audit/, and (indirectly) mcp_server/ — all layers speak this dialect.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


# ── Severity levels ──────────────────────────────────────────────────────────

Severity = Literal["low", "medium", "high", "critical"]

# Ordered mapping used by the policy engine to compare severities
SEVERITY_RANK: dict[Severity, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

# ── Decision values ───────────────────────────────────────────────────────────

Decision = Literal["ALLOW", "WARN_CONFIRM", "BLOCK"]

# Ordered mapping used by the policy engine to compare decisions
DECISION_RANK: dict[Decision, int] = {
    "ALLOW": 0,
    "WARN_CONFIRM": 1,
    "BLOCK": 2,
}


# ── Detector output ───────────────────────────────────────────────────────────

class DetectorMatch(BaseModel):
    """A single sensitive-data match produced by one detector."""

    detector_name: str = Field(
        ...,
        description="Canonical name of the detector that produced this match (e.g. 'api_key').",
    )
    severity: Severity = Field(
        ...,
        description="Severity level assigned by the detector.",
    )
    masked_value: str = Field(
        ...,
        description=(
            "Obfuscated representation of the matched value "
            "(e.g. 'AKIA****'). Raw values are NEVER stored."
        ),
    )
    span: tuple[int, int] = Field(
        ...,
        description="Start and end character offsets (inclusive) of the match within the scanned text.",
    )
    match_type: str = Field(
        default="",
        description="Optional sub-type label (e.g. 'aws_access_key', 'visa_card').",
    )


# ── Policy engine output ──────────────────────────────────────────────────────

class PolicyDecision(BaseModel):
    """The aggregated decision produced by the policy engine for a set of matches."""

    action: Decision = Field(
        ...,
        description="Final security decision: ALLOW | WARN_CONFIRM | BLOCK.",
    )
    reason: str = Field(
        ...,
        description="Human-readable explanation of why this decision was reached.",
    )
    highest_severity: Severity | None = Field(
        default=None,
        description="The highest severity among all matches (None if no matches).",
    )


# ── Scanner output (the top-level result returned to callers) ─────────────────

class ScanResult(BaseModel):
    """
    The complete output of core.scanner.scan_prompt().

    This is what the MCP tool handler translates into an MCP tool response.
    It must never contain raw sensitive values.
    """

    decision: Decision = Field(
        ...,
        description="Top-level security decision.",
    )
    matches: list[DetectorMatch] = Field(
        default_factory=list,
        description="All detector matches (masked values only).",
    )
    reason: str = Field(
        ...,
        description="Human-readable explanation for the decision.",
    )
    scanned_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="UTC timestamp of when the scan was performed.",
    )

    @property
    def matched_detector_names(self) -> list[str]:
        """Convenience list of unique detector names that produced matches."""
        return list(dict.fromkeys(m.detector_name for m in self.matches))
