"""
detectors/credit_card.py
------------------------
Detects credit/debit card numbers using regex pattern matching
followed by Luhn checksum validation (via python-stdnum).

Patterns detected:
- Visa (16 digits, 4xxx prefix)
- Mastercard (16 digits, 5xxx / 2xxx prefix)
- American Express (15 digits, 34xx / 37xx prefix)
- Discover (16 digits, 6011 / 65xx prefix)
- Generic 13–19 digit numeric sequences (Luhn-validated)

False-positive reduction:
- Luhn validation filters out random number sequences.
- Minimum digit count of 13 prevents short numeric IDs from matching.

ARCHITECTURAL CONSTRAINT: No MCP, SSE, OAuth, or Starlette types here.
"""

from __future__ import annotations

import re

from stdnum import luhn  # python-stdnum

from core.models import DetectorMatch
from detectors.base import BaseDetector
from detectors.registry import register

# Match 13–19 digit sequences with optional spaces/dashes as separators
# e.g. "4111 1111 1111 1111" or "4111-1111-1111-1111" or "4111111111111111"
_CARD_PATTERN = re.compile(
    r"\b(?:\d[ -]?){12,18}\d\b"
)

# Strip separators before Luhn check
_STRIP_SEPARATORS = re.compile(r"[ -]")


@register("credit_card")
class CreditCardDetector(BaseDetector):
    """Detects credit card numbers with Luhn checksum validation."""

    @property
    def name(self) -> str:
        return "credit_card"

    def detect(self, text: str) -> list[DetectorMatch]:
        matches: list[DetectorMatch] = []

        for m in _CARD_PATTERN.finditer(text):
            raw_match = m.group(0)
            digits_only = _STRIP_SEPARATORS.sub("", raw_match)

            # Must be 13–19 digits after stripping separators
            if not (13 <= len(digits_only) <= 19):
                continue

            # Luhn validation — filters out ~90% of false positives
            if not luhn.is_valid(digits_only):
                continue

            card_type = self._classify(digits_only)

            matches.append(
                DetectorMatch(
                    detector_name=self.name,
                    severity="high",
                    masked_value=self.mask(digits_only, visible_prefix=4),
                    span=(m.start(), m.end()),
                    match_type=card_type,
                )
            )

        return matches

    @staticmethod
    def _classify(digits: str) -> str:
        """Classify card by BIN prefix."""
        if digits.startswith("4"):
            return "visa"
        if digits[:2] in ("34", "37"):
            return "amex"
        if digits[:4] in ("6011", "6441", "6445", "6450", "6500") or digits[:2] == "65":
            return "discover"
        first2 = int(digits[:2])
        if (51 <= first2 <= 55) or (22 <= int(digits[:4]) <= 2720):
            return "mastercard"
        return "generic_card"
