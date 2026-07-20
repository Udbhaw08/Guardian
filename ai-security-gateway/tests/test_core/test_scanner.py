"""
tests/test_core/test_scanner.py
--------------------------------
Tests for core.scanner.scan_prompt().

Key proofs:
1. Protocol agnosticism — scanner has NO hidden MCP/auth dependency
2. Extensibility — a new detector added in a new file is auto-discovered
   with zero edits to scanner.py
3. End-to-end scan with known-sensitive input returns expected decisions
"""

from __future__ import annotations

import sys
import importlib
import textwrap
import types

import pytest

from core.scanner import scan_prompt
from core.models import ScanResult


class TestProtocolAgnosticism:
    """
    Prove that core.scanner has no hidden dependency on MCP, Starlette,
    or any transport/auth layer.
    """

    def test_scanner_has_no_mcp_imports(self):
        """
        core.scanner must not import from mcp_server/, mcp, starlette,
        uvicorn, or fastapi.
        """
        forbidden_prefixes = ("mcp_server", "mcp", "starlette", "uvicorn", "fastapi")

        scanner_module = importlib.import_module("core.scanner")
        scanner_source = sys.modules["core.scanner"].__file__

        # Check all modules that were imported as a side-effect of importing scanner
        # We look at the scanner module's own namespace/globals for forbidden imports
        for attr_name in dir(scanner_module):
            attr = getattr(scanner_module, attr_name, None)
            if isinstance(attr, types.ModuleType):
                mod_name = attr.__name__
                for prefix in forbidden_prefixes:
                    assert not mod_name.startswith(prefix), (
                        f"core.scanner imported '{mod_name}' which starts with "
                        f"forbidden prefix '{prefix}'. "
                        f"Transport/auth must not leak into core/."
                    )

    def test_scan_prompt_callable_without_server(self):
        """
        scan_prompt() must be callable directly with no server/event loop running.
        This proves the core is protocol-agnostic.
        """
        result = scan_prompt("Hello, no secrets here.")
        assert isinstance(result, ScanResult)
        assert result.decision == "ALLOW"

    def test_return_type_has_no_mcp_types(self):
        """ScanResult must be a plain Pydantic model with no MCP SDK types."""
        result = scan_prompt("test text")
        # Verify it's a plain Pydantic BaseModel, not an MCP type
        from pydantic import BaseModel
        assert isinstance(result, BaseModel)
        # No MCP-specific attributes
        assert not hasattr(result, "content")  # MCP TextContent would have this
        assert not hasattr(result, "isError")  # MCP tool error would have this


class TestExtensibility:
    """
    Prove that adding a new detector file is sufficient for scan_prompt()
    to pick it up — zero edits to scanner.py or any other existing file.
    """

    def test_dummy_detector_auto_discovered(self, tmp_path, monkeypatch):
        """
        Create a dummy detector module dynamically, inject it into the
        detectors package path, reload the registry, confirm scan_prompt()
        uses it.
        """
        import detectors
        from detectors import registry

        # Write a dummy detector file to a temp location
        dummy_source = textwrap.dedent("""\
            from core.models import DetectorMatch
            from detectors.base import BaseDetector
            from detectors.registry import register

            @register("dummy_test_detector")
            class DummyDetector(BaseDetector):
                @property
                def name(self):
                    return "dummy_test_detector"

                def detect(self, text):
                    if "TRIGGER_DUMMY" in text:
                        return [DetectorMatch(
                            detector_name=self.name,
                            severity="low",
                            masked_value="TRIG****",
                            span=(0, 12),
                            match_type="dummy",
                        )]
                    return []
        """)

        dummy_file = tmp_path / "dummy_test_detector.py"
        dummy_file.write_text(dummy_source)

        # Inject tmp_path into the detectors package __path__
        original_path = list(detectors.__path__)
        monkeypatch.setattr(detectors, "__path__", [str(tmp_path)] + original_path)

        # Reset the loaded flag so load_all_detectors() re-scans
        monkeypatch.setattr(registry, "_detectors_loaded", False)

        # Re-run the loader
        registry.load_all_detectors()

        # Confirm dummy detector is now registered
        assert "dummy_test_detector" in registry.DETECTOR_REGISTRY, (
            "Dummy detector should be auto-discovered by load_all_detectors()"
        )

        # Confirm scan_prompt() uses it without any scanner.py edit
        result = scan_prompt("TRIGGER_DUMMY content here")
        dummy_matches = [m for m in result.matches if m.detector_name == "dummy_test_detector"]
        assert dummy_matches, (
            "scan_prompt() should pick up the dummy detector automatically"
        )


class TestEndToEnd:
    """End-to-end scan scenarios."""

    def test_clean_text_returns_allow(self):
        result = scan_prompt("What is the capital of France?")
        assert result.decision == "ALLOW"
        assert len(result.matches) == 0

    def test_aws_key_returns_block(self):
        result = scan_prompt("My AWS key is AKIAIOSFODNN7EXAMPLE")
        assert result.decision == "BLOCK"
        assert any(m.detector_name == "api_key" for m in result.matches)

    def test_credit_card_returns_warn_or_block(self):
        # Luhn-valid Visa test number
        result = scan_prompt("Please charge 4111111111111111 for the order")
        assert result.decision in ("WARN_CONFIRM", "BLOCK")
        assert any(m.detector_name == "credit_card" for m in result.matches)

    def test_ssn_in_text_detected(self):
        result = scan_prompt("Patient SSN: 123-45-6789")
        assert result.decision in ("WARN_CONFIRM", "BLOCK")
        assert any(m.detector_name == "national_id" for m in result.matches)

    def test_result_contains_no_raw_sensitive_values(self):
        """HARD CONSTRAINT: Raw sensitive values must never appear in ScanResult."""
        secret = "AKIAIOSFODNN7EXAMPLE"
        result = scan_prompt(f"key={secret}")
        for match in result.matches:
            assert secret not in match.masked_value, (
                "Raw API key must not appear in masked_value"
            )
        assert secret not in result.reason

    def test_scanned_at_is_set(self):
        result = scan_prompt("some text")
        assert result.scanned_at is not None
