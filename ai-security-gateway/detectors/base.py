"""
detectors/base.py
-----------------
Abstract base class for all sensitive-data detectors.

ARCHITECTURAL CONSTRAINT: No MCP, SSE, OAuth, or Starlette types allowed here.
Detectors are pure Python: text in → list[DetectorMatch] out.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import DetectorMatch


class BaseDetector(ABC):
    """
    Contract that every detector must fulfil.

    To add a new detector:
    1. Create a new file in detectors/ (e.g. detectors/my_detector.py).
    2. Subclass BaseDetector and implement detect().
    3. Decorate the class with @register("my_detector") from detectors.registry.
    4. Done — zero edits to scanner.py or any other file.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical snake_case name of this detector (matches the @register key)."""
        ...

    @abstractmethod
    def detect(self, text: str) -> list[DetectorMatch]:
        """
        Scan *text* for sensitive data patterns.

        Args:
            text: The raw prompt/message text to scan.

        Returns:
            A list of DetectorMatch objects. Each match must use a masked_value
            — the raw sensitive value must never be stored or returned.
        """
        ...

    @staticmethod
    def mask(value: str, visible_prefix: int = 4) -> str:
        """
        Produce a masked representation of a sensitive value.

        Example:
            mask("sk-live-abc123xyz") -> "sk-l****"
            mask("4111111111111111") -> "4111****"
        """
        if len(value) <= visible_prefix:
            return "*" * len(value)
        return value[:visible_prefix] + "****"
