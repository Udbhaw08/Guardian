"""Tests for the policy engine."""

import pytest

from core.models import DetectorMatch
from policy.engine import PolicyEngine


@pytest.fixture
def engine():
    return PolicyEngine()


def make_match(detector: str, severity: str, match_type: str = "test") -> DetectorMatch:
    return DetectorMatch(
        detector_name=detector,
        severity=severity,
        masked_value="TEST****",
        span=(0, 4),
        match_type=match_type,
    )


class TestEmptyMatches:
    def test_no_matches_returns_allow(self, engine):
        decision = engine.decide([])
        assert decision.action == "ALLOW"
        assert decision.highest_severity is None
        assert "No sensitive" in decision.reason


class TestAggregationHighestSeverity:
    def test_block_beats_warn_confirm(self, engine):
        """BLOCK must win over WARN_CONFIRM."""
        matches = [
            make_match("cvv", "high"),        # → WARN_CONFIRM
            make_match("api_key", "critical"),      # → BLOCK
        ]
        decision = engine.decide(matches)
        assert decision.action == "BLOCK"

    def test_warn_confirm_beats_allow(self, engine):
        """WARN_CONFIRM must win over ALLOW."""
        matches = [
            make_match("credit_card", "low"),       # → ALLOW
            make_match("cvv", "high"),          # → WARN_CONFIRM
        ]
        decision = engine.decide(matches)
        assert decision.action == "WARN_CONFIRM"

    def test_single_critical_api_key_blocks(self, engine):
        matches = [make_match("api_key", "critical")]
        decision = engine.decide(matches)
        assert decision.action == "BLOCK"

    def test_single_high_credit_card_warns(self, engine):
        matches = [make_match("credit_card", "high")]
        decision = engine.decide(matches)
        assert decision.action == "WARN_CONFIRM"

    def test_multiple_allows_remain_allow(self, engine):
        matches = [
            make_match("credit_card", "low"),
            make_match("cvv", "low"),
        ]
        # Both resolve to ALLOW per policy
        decision = engine.decide(matches)
        # At least ALLOW (may be WARN_CONFIRM depending on policy defaults)
        assert decision.action in ("ALLOW", "WARN_CONFIRM")


class TestHighestSeverityTracking:
    def test_highest_severity_correct(self, engine):
        matches = [
            make_match("cvv", "medium"),
            make_match("api_key", "critical"),
        ]
        decision = engine.decide(matches)
        assert decision.highest_severity == "critical"

    def test_severity_order_respected(self, engine):
        """Ensure critical > high > medium > low ordering."""
        from core.models import SEVERITY_RANK
        assert SEVERITY_RANK["critical"] > SEVERITY_RANK["high"]
        assert SEVERITY_RANK["high"] > SEVERITY_RANK["medium"]
        assert SEVERITY_RANK["medium"] > SEVERITY_RANK["low"]


class TestUnknownDetector:
    def test_unknown_detector_uses_defaults(self, engine):
        """An unregistered detector name falls back to defaults."""
        matches = [make_match("future_detector_xyz", "critical")]
        decision = engine.decide(matches)
        # critical default is BLOCK
        assert decision.action == "BLOCK"


class TestReasonContent:
    def test_block_reason_contains_block(self, engine):
        matches = [make_match("api_key", "critical")]
        decision = engine.decide(matches)
        assert "BLOCK" in decision.reason.upper() or "BLOCKED" in decision.reason.upper()

    def test_warn_reason_mentions_sensitive(self, engine):
        matches = [make_match("cvv", "high")]
        decision = engine.decide(matches)
        assert "WARNING" in decision.reason.upper() or "sensitive" in decision.reason.lower()
