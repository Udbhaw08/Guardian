"""
policy/schema.py
----------------
Pydantic v2 schema for policies.yaml.

Validates the YAML structure at load time so misconfigured policies
fail loudly at startup, not silently during a scan.

ARCHITECTURAL CONSTRAINT: No MCP, SSE, OAuth, or Starlette types here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from core.models import Decision, Severity

# All valid severity / action combinations
_VALID_SEVERITIES: frozenset[str] = frozenset({"low", "medium", "high", "critical"})
_VALID_DECISIONS: frozenset[str] = frozenset({"ALLOW", "WARN_CONFIRM", "BLOCK"})
_VALID_AGGREGATION_RULES: frozenset[str] = frozenset({"highest_severity"})


class DetectorPolicyEntry(BaseModel):
    """
    Per-detector severity → action mapping.
    Not all severity levels need to be listed; missing ones fall through
    to the defaults block.
    """

    low: Decision | None = None
    medium: Decision | None = None
    high: Decision | None = None
    critical: Decision | None = None

    def get_action(self, severity: Severity) -> Decision | None:
        """Return the configured action for *severity*, or None if not set."""
        return getattr(self, severity)


class DefaultPolicyEntry(BaseModel):
    """Fallback actions used when a detector or severity is not explicitly listed."""

    low: Decision = "ALLOW"
    medium: Decision = "WARN_CONFIRM"
    high: Decision = "WARN_CONFIRM"
    critical: Decision = "BLOCK"

    def get_action(self, severity: Severity) -> Decision:
        return getattr(self, severity)


class PolicyConfig(BaseModel):
    """
    Root schema for policies.yaml.

    Example YAML:
        aggregation_rule: highest_severity
        detectors:
          api_key:
            critical: BLOCK
            high: WARN_CONFIRM
        defaults:
          critical: BLOCK
          high: WARN_CONFIRM
          medium: WARN_CONFIRM
          low: ALLOW
    """

    aggregation_rule: Literal["highest_severity"] = Field(
        default="highest_severity",
        description="How to combine multiple detector matches into one decision.",
    )
    detectors: dict[str, DetectorPolicyEntry] = Field(
        default_factory=dict,
        description="Per-detector severity→action overrides.",
    )
    defaults: DefaultPolicyEntry = Field(
        default_factory=DefaultPolicyEntry,
        description="Fallback actions for unknown detectors or unlisted severity levels.",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_aggregation_rule(cls, data: dict) -> dict:
        rule = data.get("aggregation_rule", "highest_severity")
        if rule not in _VALID_AGGREGATION_RULES:
            raise ValueError(
                f"Invalid aggregation_rule '{rule}'. "
                f"Valid values: {sorted(_VALID_AGGREGATION_RULES)}"
            )
        return data

    def resolve_action(self, detector_name: str, severity: Severity) -> Decision:
        """
        Look up the action for a given (detector_name, severity) pair.

        Precedence:
        1. Explicit entry in detectors[detector_name][severity]
        2. defaults[severity]
        """
        detector_entry = self.detectors.get(detector_name)
        if detector_entry:
            action = detector_entry.get_action(severity)
            if action is not None:
                return action
        return self.defaults.get_action(severity)
