"""
detectors/aggregator.py
------------------------
Confidence Aggregator — Stage 4 (final) of the prompt injection detection pipeline.

This is the ONLY place in the pipeline where a final blocking decision is made.
It combines three independent signals into a weighted confidence score and maps
that score to a severity level (or None if below threshold → ALLOW).

Signal weights:
    ML score:    0.45  (primary signal — trained on real injection data)
    Rule score:  0.35  (high-precision verbatim templates)
    Verifier:    0.20  (context adjustment — positive or negative)

Confidence → Severity mapping:
    ≥ 0.80  → critical  (BLOCK via policy)
    ≥ 0.65  → high      (BLOCK via policy)
    ≥ 0.50  → medium    (WARN_CONFIRM via policy — softened from old BLOCK)
    ≥ 0.38  → low       (WARN_CONFIRM via policy)
    < 0.38  → None      (ALLOW — not flagged at all)

Usage (called from prompt_injection.py):
    from detectors.aggregator import aggregate
    result = aggregate(rule_score, ml_score, verifier_adjustment, optimal_threshold)
"""

from __future__ import annotations

from dataclasses import dataclass

from core.models import Severity


# Signal weights — must sum to 1.0
_WEIGHT_ML       = 0.45
_WEIGHT_RULE     = 0.35
_WEIGHT_VERIFIER = 0.20

assert abs(_WEIGHT_ML + _WEIGHT_RULE + _WEIGHT_VERIFIER - 1.0) < 1e-9, \
    "Aggregator weights must sum to 1.0"


@dataclass(frozen=True)
class AggregationResult:
    """Complete output from the confidence aggregator."""
    rule_score: float
    ml_score: float
    verifier_adjustment: float
    confidence: float                   # final weighted score [0, 1]
    severity: Severity | None           # None = below threshold → ALLOW
    decision_reason: str                # human-readable explanation


def _score_to_severity(confidence: float) -> Severity | None:
    """
    Map a continuous confidence score to a discrete severity level.

    Thresholds are calibrated so that:
    - 'critical'/'high' → BLOCK (clear attacks, high certainty)
    - 'medium'/'low'    → WARN_CONFIRM (uncertain, let user decide)
    - None              → ALLOW (confident it's safe)
    """
    if confidence >= 0.80:
        return "critical"
    if confidence >= 0.65:
        return "high"
    if confidence >= 0.50:
        return "medium"
    if confidence >= 0.38:
        return "low"
    return None   # below threshold → ALLOW


def _build_reason(
    confidence: float,
    severity: Severity | None,
    rule_score: float,
    ml_score: float,
    verifier_adjustment: float,
    rule_names: list[str],
    signals_reducing: list[str],
    signals_boosting: list[str],
) -> str:
    """Build a human-readable explanation of the aggregation decision."""
    if severity is None:
        parts = [f"confidence={confidence:.3f} (below threshold → ALLOW)"]
        if signals_reducing:
            parts.append(f"context signals reduced score: {', '.join(signals_reducing)}")
        return ". ".join(parts)

    parts = [f"confidence={confidence:.3f} → {severity}"]
    if rule_names:
        parts.append(f"rules matched: {', '.join(rule_names)}")
    if signals_boosting:
        parts.append(f"attack signals: {', '.join(signals_boosting)}")
    if signals_reducing:
        parts.append(f"mitigating context: {', '.join(signals_reducing)}")
    parts.append(
        f"(ml={ml_score:.3f}×{_WEIGHT_ML} + "
        f"rule={rule_score:.3f}×{_WEIGHT_RULE} + "
        f"verifier={verifier_adjustment:+.3f}×{_WEIGHT_VERIFIER})"
    )
    return ". ".join(parts)


def aggregate(
    rule_score: float,
    ml_score: float,
    verifier_adjustment: float,
    rule_names: list[str] | None = None,
    signals_reducing: list[str] | None = None,
    signals_boosting: list[str] | None = None,
) -> AggregationResult:
    """
    Combine all pipeline signals into a final severity decision.

    Args:
        rule_score:           Output of get_rule_score() from injection_rules.py [0,1]
        ml_score:             predict_proba score for class 1 from the ML model [0,1]
        verifier_adjustment:  Net context adjustment from verifier.py [-0.50, +0.40]
        rule_names:           Names of rules that fired (for logging/reason string)
        signals_reducing:     Context signals that reduced confidence (for logging)
        signals_boosting:     Context signals that boosted confidence (for logging)

    Returns:
        AggregationResult with final confidence, severity, and reason.
    """
    rule_names = rule_names or []
    signals_reducing = signals_reducing or []
    signals_boosting = signals_boosting or []

    # Weighted combination: verifier adjustment is treated as an additive offset
    # on the weighted ML+rule score, then clamped to [0, 1].
    raw_confidence = (
        _WEIGHT_ML   * ml_score
        + _WEIGHT_RULE * rule_score
        + _WEIGHT_VERIFIER * verifier_adjustment
    )
    confidence = round(max(0.0, min(1.0, raw_confidence)), 4)
    severity   = _score_to_severity(confidence)

    reason = _build_reason(
        confidence, severity,
        rule_score, ml_score, verifier_adjustment,
        rule_names, signals_reducing, signals_boosting,
    )

    return AggregationResult(
        rule_score=round(rule_score, 4),
        ml_score=round(ml_score, 4),
        verifier_adjustment=round(verifier_adjustment, 4),
        confidence=confidence,
        severity=severity,
        decision_reason=reason,
    )
