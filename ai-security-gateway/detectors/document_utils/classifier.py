"""
detectors/document_utils/classifier.py
-----------------------------------------
Shared wrapper around the existing injection_model.pkl.

This module is the single bridge between the document scanning pipeline and
the trained ML model. Both PDF and Image scanners call classify_text() here.

ARCHITECTURAL CONSTRAINT: No MCP, SSE, or transport types here.
"""

from __future__ import annotations

import os
import warnings

import joblib

# ── Module-level model cache — loaded once on first call ──────────────────────
_MODEL = None


def _get_model():
    """Lazy-load the trained injection model from disk. Cached after first call."""
    global _MODEL
    if _MODEL is None:
        model_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "models", "injection_model.pkl"
        )
        model_path = os.path.normpath(model_path)
        # Suppress scikit-learn version mismatch warnings during load
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _MODEL = joblib.load(model_path)
    return _MODEL


def classify_text(text: str) -> tuple[bool, float]:
    """
    Classify a text string for prompt injection using the trained ML model.

    This function works identically whether the text came from:
    - A typed user prompt
    - Extracted PDF text (including hidden text)
    - OCR output from an image

    Args:
        text: The text to classify.

    Returns:
        A tuple of (is_injection: bool, confidence: float).
        - is_injection: True if the model predicts injection (label=1).
        - confidence: Probability score from 0.0 to 1.0.
                      Higher = more confident it is an injection.

    Notes:
        - Returns (False, 0.0) for empty or whitespace-only text.
        - Thread-safe — model is stateless after loading.
    """
    if not text or not text.strip():
        return False, 0.0

    model = _get_model()

    # predict_proba returns [[prob_class_0, prob_class_1]]
    proba = model.predict_proba([text])[0]
    confidence = float(proba[1])  # probability of being an injection (class=1)
    is_injection = confidence >= 0.45

    return is_injection, confidence
