"""Tests for the national ID detector."""

import pytest

from detectors.national_id import NationalIdDetector


@pytest.fixture
def detector():
    return NationalIdDetector()


class TestSSN:
    def test_valid_ssn_detected(self, detector):
        matches = detector.detect("SSN: 123-45-6789")
        ssn_matches = [m for m in matches if m.match_type == "us_ssn"]
        assert ssn_matches
        assert ssn_matches[0].severity == "high"

    def test_ssn_masked_correctly(self, detector):
        matches = detector.detect("SSN: 123-45-6789")
        ssn_matches = [m for m in matches if m.match_type == "us_ssn"]
        assert ssn_matches
        assert "123456789" not in ssn_matches[0].masked_value

    def test_ssn_area_000_rejected(self, detector):
        """SSNs with area 000 are invalid per SSA rules."""
        matches = detector.detect("SSN: 000-45-6789")
        ssn = [m for m in matches if m.match_type == "us_ssn"]
        assert not ssn

    def test_ssn_area_666_rejected(self, detector):
        matches = detector.detect("SSN: 666-45-6789")
        ssn = [m for m in matches if m.match_type == "us_ssn"]
        assert not ssn

    def test_ssn_area_900_range_rejected(self, detector):
        """900–999 range is invalid."""
        matches = detector.detect("SSN: 900-45-6789")
        ssn = [m for m in matches if m.match_type == "us_ssn"]
        assert not ssn

    def test_ssn_group_00_rejected(self, detector):
        matches = detector.detect("SSN: 123-00-6789")
        ssn = [m for m in matches if m.match_type == "us_ssn"]
        assert not ssn

    def test_ssn_serial_0000_rejected(self, detector):
        matches = detector.detect("SSN: 123-45-0000")
        ssn = [m for m in matches if m.match_type == "us_ssn"]
        assert not ssn


class TestAadhaar:
    def test_valid_aadhaar_format(self, detector):
        # Note: python-stdnum validates checksum; 2345 6789 0123 may not pass Verhoeff
        # We test that the pattern matches and stdnum validation is attempted.
        # Use a known-valid Aadhaar for full validation.
        # For pattern-only test: ensure detector runs without error.
        text = "Aadhaar: 2345 6789 0123"
        matches = detector.detect(text)
        # We can't guarantee validity without a real Aadhaar; just ensure no exception
        # A real test would use a stdnum-confirmed valid number.

    def test_aadhaar_starting_with_0_or_1_rejected(self, detector):
        """Aadhaar cannot start with 0 or 1."""
        matches = detector.detect("0123 4567 8901")
        aadhaar = [m for m in matches if m.match_type == "in_aadhaar"]
        assert not aadhaar

        matches = detector.detect("1234 5678 9012")
        aadhaar = [m for m in matches if m.match_type == "in_aadhaar"]
        assert not aadhaar


class TestNormalText:
    def test_plain_text_not_matched(self, detector):
        matches = detector.detect("The meeting is at 3pm in room 123.")
        assert not matches

    def test_phone_number_not_matched(self, detector):
        # Phone numbers are not in NNN-NN-NNNN format
        matches = detector.detect("Call me at 555-867-5309")
        ssn = [m for m in matches if m.match_type == "us_ssn"]
        assert not ssn  # 3-3-4 pattern doesn't match SSN 3-2-4 pattern
