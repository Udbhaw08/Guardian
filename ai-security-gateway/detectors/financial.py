"""
detectors/financial.py
----------------------
Detects company internal financial details like Bank Accounts, IFSC, and GSTIN.

ARCHITECTURAL CONSTRAINT: No MCP, SSE, OAuth, or Starlette types here.
"""

from __future__ import annotations

import re

from core.models import DetectorMatch
from detectors.base import BaseDetector
from detectors.registry import register

# GSTIN: 2 digits + PAN (10 chars) + 1 digit/letter + Z + 1 digit/letter (last char is a checksum)
_GSTIN_PATTERN = re.compile(r"\b(\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]Z[A-Z\d])\b", re.IGNORECASE)

try:
    from stdnum.in_ import gstin as _gstin_module

    def _is_valid_gstin(raw: str) -> bool:
        """Validate GSTIN's checksum digit via python-stdnum."""
        return _gstin_module.is_valid(raw)

except ImportError:
    def _is_valid_gstin(_raw: str) -> bool:  # type: ignore[misc]
        return True

# IFSC: 4 letters, '0', 6 alphanumeric
_IFSC_PATTERN = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b", re.IGNORECASE)

# Bank Account: Context-aware 9-18 digit number.
# Keyword, then an optional "no."/"number"/"#" qualifier (covers "A/C No", "Account Number",
# "Acc No.", etc. — not just the bare keyword immediately touching the digits), then the
# existing punctuation/whitespace separator before the digits themselves.
_BANK_ACC_PATTERN = re.compile(
    r"(?i)\b(?:a/c|account|acc|bank\s?a/c|acct)"
    r"(?:[^\S\r\n]*(?:no\.?|number|#))?"
    r"[^\S\r\n]*[:.#-]*[^\S\r\n]*(\d{9,18})\b"
)


@register("financial")
class FinancialDetector(BaseDetector):
    """Detects company internal financial details (GSTIN, Bank A/C, IFSC)."""

    @property
    def name(self) -> str:
        return "financial"

    def detect(self, text: str) -> list[DetectorMatch]:
        matches: list[DetectorMatch] = []
        
        # GSTIN
        for m in _GSTIN_PATTERN.finditer(text):
            raw = m.group(1).upper()
            if not _is_valid_gstin(raw):
                continue
            matches.append(
                DetectorMatch(
                    detector_name=self.name,
                    severity="medium",
                    masked_value=self.mask(raw, visible_prefix=2),
                    span=(m.start(1), m.end(1)),
                    match_type="in_gstin",
                )
            )

        # IFSC
        for m in _IFSC_PATTERN.finditer(text):
            raw = m.group(1).upper()
            matches.append(
                DetectorMatch(
                    detector_name=self.name,
                    severity="low",
                    masked_value=self.mask(raw, visible_prefix=4),
                    span=(m.start(1), m.end(1)),
                    match_type="in_ifsc",
                )
            )

        # Bank Account
        for m in _BANK_ACC_PATTERN.finditer(text):
            raw = m.group(1)
            matches.append(
                DetectorMatch(
                    detector_name=self.name,
                    severity="high",
                    masked_value=self.mask(raw, visible_prefix=2),
                    span=(m.start(1), m.end(1)),
                    match_type="bank_account",
                )
            )

        return matches
