"""
detectors/prompt_injection.py
------------------------------
Detects LLM prompt injection and jailbreak attempts.

ARCHITECTURE:
    This detector is the orchestrator of a 4-stage multi-signal pipeline.
    It is the ONLY registered detector for prompt injection — the three
    helper modules (injection_rules, verifier, aggregator) are internal
    implementation details NOT registered in the detector registry.

    Stage 1 — Rule Signal (injection_rules.py)
        High-precision regex patterns for verbatim attack templates.
        Output: rule_score [0,1]

    Stage 2 — ML Classifier
        TF-IDF + Calibrated LogisticRegression → predict_proba.
        Output: ml_score [0,1]
        For long texts: chunk-level scoring (average over text windows)
        to prevent injection dilution in long documents.

    Stage 3 — Context Verifier (verifier.py)
        Checks for intent signals — educational, programming, question,
        document context → reduces confidence.
        Checks for obfuscation and harmful domain → boosts confidence.
        Output: verifier_adjustment [-0.50, +0.40]

    Stage 4 — Confidence Aggregator (aggregator.py)
        Combines all signals with fixed weights:
            ml * 0.45 + rule * 0.35 + verifier * 0.20
        Maps final confidence to severity or None (→ ALLOW).
        Output: AggregationResult with severity and reason.

EXTERNAL CONTRACT (unchanged from v1):
    detect(text: str) -> list[DetectorMatch]

    The scanner.py and policy engine see no difference. The only change is
    that DetectorMatch.severity is now dynamic (not hardcoded "high"), and
    returns an empty list (ALLOW) for uncertain/low-confidence cases.
"""

from __future__ import annotations

import json
import os
import time
from typing import Iterator

import joblib

from audit.logger import log_pipeline_stage
from core.models import DetectorMatch
from detectors.aggregator import aggregate
from detectors.base import BaseDetector
from detectors.injection_rules import RuleMatch, evaluate_rules, get_rule_score
from detectors.registry import register
from detectors.verifier import verify

# ── Model + threshold loading (cached) ────────────────────────────────────────

_MODEL = None
_THRESHOLD: float = 0.55    # fallback default


def _get_model():
    """Load the trained sklearn pipeline, cached after first call."""
    global _MODEL
    if _MODEL is None:
        model_path = os.path.join(
            os.path.dirname(__file__), "..", "models", "injection_model.pkl"
        )
        _MODEL = joblib.load(model_path)
    return _MODEL


def _get_threshold() -> float:
    """
    Load the optimal threshold from models/optimal_threshold.json.
    Falls back to 0.55 if the file doesn't exist (e.g., first run before training).
    """
    global _THRESHOLD
    threshold_path = os.path.join(
        os.path.dirname(__file__), "..", "models", "optimal_threshold.json"
    )
    if os.path.exists(threshold_path):
        with open(threshold_path) as f:
            _THRESHOLD = json.load(f).get("threshold", 0.55)
    return _THRESHOLD


# Chunk configuration for long-text scoring
_CHUNK_SIZE   = 300   # characters per chunk
_CHUNK_STRIDE = 150   # overlap between chunks (50% stride)
_CHUNK_FLAG_RATIO = float(os.getenv("CHUNK_FLAG_RATIO", "0.40"))


def _chunk_ml_score(model, text: str, threshold: float) -> float:
    """
    Score long texts by splitting into overlapping chunks, getting
    predict_proba for each, and returning the average.

    This prevents a long benign document from diluting a short injected
    instruction embedded within it (the old line-by-line hard-predict approach
    caused FPs; this uses soft scores averaged).

    Args:
        model:     The loaded sklearn pipeline.
        text:      The full input text.
        threshold: The optimal classification threshold.

    Returns:
        Average injection probability across all chunks, as a float [0,1].
    """
    if len(text) <= _CHUNK_SIZE:
        # Short text: score as-is
        return float(model.predict_proba([text])[0, 1])

    chunks: list[str] = []
    for start in range(0, len(text), _CHUNK_STRIDE):
        chunk = text[start: start + _CHUNK_SIZE].strip()
        if chunk:
            chunks.append(chunk)

    if not chunks:
        return float(model.predict_proba([text])[0, 1])

    probs = model.predict_proba(chunks)[:, 1]
    # Flag if more than CHUNK_FLAG_RATIO of chunks exceed the threshold
    flagged_ratio = (probs >= threshold).mean()
    # Final score: average of all chunk probabilities, boosted if many chunks flag
    avg_prob = float(probs.mean())
    if flagged_ratio >= _CHUNK_FLAG_RATIO:
        # Multiple chunks look like injection — amplify slightly
        avg_prob = min(1.0, avg_prob * 1.15)
    return avg_prob


# ── Detector ──────────────────────────────────────────────────────────────────

@register("prompt_injection")
class PromptInjectionDetector(BaseDetector):
    """
    Detects LLM prompt injection and jailbreak attempts using a 4-stage
    multi-signal verification pipeline.

    The external interface (detect() → list[DetectorMatch]) is identical
    to v1. Internally, instead of a direct model.predict() call, the text
    passes through rule scoring, ML scoring, context verification, and
    confidence aggregation before a severity is assigned.
    """

    @property
    def name(self) -> str:
        return "prompt_injection"

    def detect(self, text: str, request_id: str | None = None) -> list[DetectorMatch]:
        """
        Run the 4-stage pipeline and return DetectorMatch(es) if injection is detected.

        Args:
            text:       The raw input text to scan.
            request_id: Optional ID for correlating stage logs (passed from scanner).

        Returns:
            list[DetectorMatch] — empty list means ALLOW (no injection detected).
            Each match has a dynamic severity (critical/high/medium/low) based
            on the aggregated confidence score.
        """
        threshold = _get_threshold()
        model     = _get_model()
        t_start   = time.monotonic()

        # ── Stage 1: Rule-Based Signal ─────────────────────────────────────────
        t1 = time.monotonic()
        rule_matches: list[RuleMatch] = evaluate_rules(text)
        rule_score: float = get_rule_score(rule_matches)
        rule_names: list[str] = [m.rule_name for m in rule_matches]
        t1_ms = (time.monotonic() - t1) * 1000

        log_pipeline_stage(
            stage="rule_filter",
            request_id=request_id,
            result="MATCH" if rule_matches else "PASS",
            matched_rules=rule_names,
            rule_score=rule_score,
            duration_ms=round(t1_ms, 2),
        )

        # ── Stage 2: ML Classifier ────────────────────────────────────────────
        t2 = time.monotonic()
        ml_score: float = _chunk_ml_score(model, text, threshold)
        t2_ms = (time.monotonic() - t2) * 1000

        log_pipeline_stage(
            stage="ml_classifier",
            request_id=request_id,
            ml_score=round(ml_score, 4),
            threshold=threshold,
            result="INJECTION" if ml_score >= threshold else "SAFE",
            duration_ms=round(t2_ms, 2),
        )

        # ── Stage 3: Context Verifier ─────────────────────────────────────────
        t3 = time.monotonic()
        verifier_result = verify(text, ml_score)
        t3_ms = (time.monotonic() - t3) * 1000

        log_pipeline_stage(
            stage="verifier",
            request_id=request_id,
            adjustment=verifier_result.adjustment,
            signals_reducing=verifier_result.signals_reducing,
            signals_boosting=verifier_result.signals_boosting,
            verdict=(
                "boosted" if verifier_result.adjustment > 0
                else "reduced" if verifier_result.adjustment < 0
                else "neutral"
            ),
            duration_ms=round(t3_ms, 2),
        )

        # ── Stage 4: Confidence Aggregator ────────────────────────────────────
        t4 = time.monotonic()
        agg = aggregate(
            rule_score=rule_score,
            ml_score=ml_score,
            verifier_adjustment=verifier_result.adjustment,
            rule_names=rule_names,
            signals_reducing=verifier_result.signals_reducing,
            signals_boosting=verifier_result.signals_boosting,
        )
        t4_ms = (time.monotonic() - t4) * 1000

        total_ms = (time.monotonic() - t_start) * 1000

        log_pipeline_stage(
            stage="aggregator",
            request_id=request_id,
            rule_score=agg.rule_score,
            ml_score=agg.ml_score,
            verifier_adjustment=agg.verifier_adjustment,
            confidence=agg.confidence,
            severity=agg.severity,
            decision="BLOCK" if agg.severity in ("critical", "high") else
                      "WARN_CONFIRM" if agg.severity in ("medium", "low") else "ALLOW",
            reason=agg.decision_reason,
            duration_ms=round(t4_ms, 2),
            total_pipeline_ms=round(total_ms, 2),
        )

        # ── Result ────────────────────────────────────────────────────────────
        if agg.severity is None:
            # Below confidence threshold — text is considered safe
            return []

        return [
            DetectorMatch(
                detector_name=self.name,
                severity=agg.severity,
                match_type="prompt_injection",
                masked_value="<PROMPT_INJECTION_REDACTED>",
                span=(0, len(text)),
            )
        ]
