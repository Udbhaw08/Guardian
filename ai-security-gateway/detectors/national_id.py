"""
detectors/national_id.py
------------------------
Detects national identification numbers.

Formats covered:
- US Social Security Number (SSN): NNN-NN-NNNN with validity rules
- India Aadhaar: 12-digit number with Verhoeff checksum (via python-stdnum)

Extensibility note:
  To add a new national ID format, add a _check_* method and call it
  from detect(). The @register decorator handles registration automatically.

ARCHITECTURAL CONSTRAINT: No MCP, SSE, OAuth, or Starlette types here.
"""

from __future__ import annotations

import re

from core.models import DetectorMatch
from detectors.base import BaseDetector
from detectors.registry import register

# ── US SSN ─────────────────────────────────────────────────────────────────────

# Standard format: 000-00-0000
_SSN_PATTERN = re.compile(r"\b(\d{3})-(\d{2})-(\d{4})\b")

# Invalid SSN area numbers per Social Security Administration rules
_INVALID_SSN_AREAS = frozenset({"000", "666"}) | {str(n) for n in range(900, 1000)}


def _is_valid_ssn(area: str, group: str, serial: str) -> bool:
    """Validate SSN components per SSA rules."""
    if area in _INVALID_SSN_AREAS:
        return False
    if group == "00":
        return False
    if serial == "0000":
        return False
    return True


# ── India Aadhaar ──────────────────────────────────────────────────────────────

# Aadhaar is a 12-digit number; may be space/hyphen separated in 4-4-4 groups
_AADHAAR_PATTERN = re.compile(
    r"\b([2-9]\d{3})[ -]?(\d{4})[ -]?(\d{4})\b"
)

try:
    from stdnum.in_ import aadhaar as _aadhaar_module

    def _is_valid_aadhaar(digits: str) -> bool:
        """Validate Aadhaar using python-stdnum's Verhoeff checksum."""
        return _aadhaar_module.is_valid(digits)

except ImportError:
    # Fallback: basic range check only (no checksum)
    def _is_valid_aadhaar(digits: str) -> bool:  # type: ignore[misc]
        return len(digits) == 12 and digits[0] in "23456789"

# ── India PAN ──────────────────────────────────────────────────────────────────

# PAN format: 5 Letters, 4 Digits, 1 Letter (e.g. AADCN4928L)
_PAN_PATTERN = re.compile(r"\b([A-Z]{5})(\d{4})([A-Z]{1})\b", re.IGNORECASE)

try:
    from stdnum.in_ import pan as _pan_module

    def _is_valid_pan(pan_str: str) -> bool:
        """Validate PAN's 4th-character holder-type code via python-stdnum."""
        return _pan_module.is_valid(pan_str)

except ImportError:
    # Fallback: the 4th character must be a real holder-type code
    # (P/C/H/F/A/T/B/L/J/G) even without the full stdnum validator.
    _PAN_HOLDER_TYPES = frozenset("PCHFATBLJG")

    def _is_valid_pan(pan_str: str) -> bool:  # type: ignore[misc]
        return len(pan_str) == 10 and pan_str[3].upper() in _PAN_HOLDER_TYPES


# ── Detector ───────────────────────────────────────────────────────────────────

@register("national_id")
class NationalIdDetector(BaseDetector):
    """Detects national identification numbers (SSN, Aadhaar)."""

    @property
    def name(self) -> str:
        return "national_id"

    def detect(self, text: str) -> list[DetectorMatch]:
        matches: list[DetectorMatch] = []
        matches.extend(self._check_ssn(text))
        matches.extend(self._check_aadhaar(text))
        matches.extend(self._check_pan(text))
        return matches

    def _check_ssn(self, text: str) -> list[DetectorMatch]:
        results = []
        for m in _SSN_PATTERN.finditer(text):
            area, group, serial = m.group(1), m.group(2), m.group(3)
            if not _is_valid_ssn(area, group, serial):
                continue
            raw = m.group(0)
            results.append(
                DetectorMatch(
                    detector_name=self.name,
                    severity="high",
                    masked_value=self.mask(raw.replace("-", ""), visible_prefix=3) ,
                    span=(m.start(), m.end()),
                    match_type="us_ssn",
                )
            )
        return results

    def _check_aadhaar(self, text: str) -> list[DetectorMatch]:
        results = []
        for m in _AADHAAR_PATTERN.finditer(text):
            digits = m.group(1) + m.group(2) + m.group(3)
            if not _is_valid_aadhaar(digits):
                continue
            results.append(
                DetectorMatch(
                    detector_name=self.name,
                    severity="high",
                    masked_value=self.mask(digits, visible_prefix=4),
                    span=(m.start(), m.end()),
                    match_type="in_aadhaar",
                )
            )
        return results

    def _check_pan(self, text: str) -> list[DetectorMatch]:
        results = []
        for m in _PAN_PATTERN.finditer(text):
            raw = m.group(0).upper()
            if not _is_valid_pan(raw):
                continue
            results.append(
                DetectorMatch(
                    detector_name=self.name,
                    severity="high",
                    masked_value=self.mask(raw, visible_prefix=2),
                    span=(m.start(), m.end()),
                    match_type="in_pan",
                )
            )
        return results
