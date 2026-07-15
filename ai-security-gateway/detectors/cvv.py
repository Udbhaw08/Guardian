"""
detectors/cvv.py
----------------
Detects CVV/CVC/security-code values only when they appear near
a relevant payment-card label.

Examples detected:
- CVV 123
- CVV: 456
- CVC=789
- security code 1234

Examples ignored:
- Room 123
- Bus 456
- Year 2026
"""

from __future__ import annotations

import re

from core.models import DetectorMatch
from detectors.base import BaseDetector
from detectors.registry import register


_CVV_PATTERN = re.compile(
    r"\b(?P<label>cvv|cvc|cid|security\s+code|card\s+verification\s+code)"
    r"\s*[:=\-]?\s*"
    r"(?P<value>\d{3,4})\b",
    re.IGNORECASE,
)


@register("cvv")
class CvvDetector(BaseDetector):
    """Detects labelled 3- or 4-digit CVV/CVC values."""

    @property
    def name(self) -> str:
        return "cvv"

    def detect(self, text: str) -> list[DetectorMatch]:
        matches: list[DetectorMatch] = []

        for match in _CVV_PATTERN.finditer(text):
            value = match.group("value")

            match_type = (
                "cvv_3_digit"
                if len(value) == 3
                else "cvv_4_digit"
            )

            matches.append(
                DetectorMatch(
                    detector_name=self.name,
                    severity="high",
                    masked_value="*" * len(value),
                    span=match.span("value"),
                    match_type=match_type,
                )
            )

        return matches