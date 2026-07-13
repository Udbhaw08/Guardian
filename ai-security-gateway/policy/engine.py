"""
policy/engine.py
----------------
Aggregates detector matches into a single PolicyDecision.

Config is loaded from POLICY_FILE_PATH env var (or defaults to
policy/policies.yaml relative to the project root).

ARCHITECTURAL CONSTRAINT: No MCP, SSE, OAuth, or Starlette types here.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

from core.models import DECISION_RANK, SEVERITY_RANK, Decision, DetectorMatch, PolicyDecision, Severity
from policy.schema import PolicyConfig


def _find_default_policy_path() -> Path:
    """
    Locate the bundled policies.yaml.
    Walks up from this file's location to find policy/policies.yaml.
    """
    here = Path(__file__).parent
    candidate = here / "policies.yaml"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"Default policy file not found at {candidate}. "
        "Set POLICY_FILE_PATH env var to specify a custom path."
    )


@lru_cache(maxsize=1)
def _load_policy_config() -> PolicyConfig:
    """
    Load and validate the policy YAML file exactly once (cached).

    The path is read from POLICY_FILE_PATH env var; falls back to the
    bundled policy/policies.yaml if not set.

    Changing POLICY_FILE_PATH at runtime requires a process restart.
    This is intentional — policy changes should be explicit deployments.
    """
    env_path = os.getenv("POLICY_FILE_PATH")
    if env_path:
        policy_path = Path(env_path)
    else:
        policy_path = _find_default_policy_path()

    with policy_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Pydantic validates the structure — raises ValueError on bad config
    return PolicyConfig.model_validate(raw)


def _highest_severity(matches: list[DetectorMatch]) -> Severity | None:
    """Return the highest severity among *matches*, or None if empty."""
    if not matches:
        return None
    return max(matches, key=lambda m: SEVERITY_RANK[m.severity]).severity


class PolicyEngine:
    """
    Aggregates a list of DetectorMatch objects into a PolicyDecision.

    The engine is stateless — safe to call concurrently.
    All configuration is read from the (cached) YAML file.
    """

    def __init__(self) -> None:
        self._config = _load_policy_config()

    def decide(self, matches: list[DetectorMatch]) -> PolicyDecision:
        """
        Aggregate *matches* and return a PolicyDecision.

        Current aggregation rule: "highest_severity"
          → iterate all matches, compute per-match action, return the
            action with the highest DECISION_RANK (BLOCK > WARN_CONFIRM > ALLOW).

        Args:
            matches: All DetectorMatch objects from a single scan_prompt() call.

        Returns:
            A PolicyDecision with action, reason, and highest_severity.
        """
        if not matches:
            return PolicyDecision(
                action="ALLOW",
                reason="No sensitive data patterns detected.",
                highest_severity=None,
            )

        # Compute per-match actions
        per_match_actions: list[tuple[Decision, DetectorMatch]] = []
        for match in matches:
            action = self._config.resolve_action(match.detector_name, match.severity)
            per_match_actions.append((action, match))

        # Apply aggregation rule: pick action with highest rank
        winning_action, winning_match = max(
            per_match_actions,
            key=lambda pair: DECISION_RANK[pair[0]],
        )

        highest_sev = _highest_severity(matches)
        detector_names = list(dict.fromkeys(m.detector_name for _, m in per_match_actions))
        reason = self._build_reason(winning_action, winning_match, detector_names)

        return PolicyDecision(
            action=winning_action,
            reason=reason,
            highest_severity=highest_sev,
        )

    def _build_reason(
        self,
        action: Decision,
        triggering_match: DetectorMatch,
        all_detector_names: list[str],
    ) -> str:
        """Construct a human-readable reason string for the decision."""
        names_str = ", ".join(all_detector_names)
        sev = triggering_match.severity
        det = triggering_match.detector_name

        if action == "BLOCK":
            return (
                f"BLOCKED: {sev.upper()} severity '{det}' pattern detected "
                f"(detectors fired: {names_str})."
            )
        if action == "WARN_CONFIRM":
            return (
                f"WARNING: Possible sensitive data found ({names_str}). "
                f"Highest severity: {sev.upper()}. "
                "Review before sending."
            )
        return f"ALLOW: No policy violation found (detectors fired: {names_str})."


# Module-level singleton — scanner.py imports this
policy_engine = PolicyEngine()
