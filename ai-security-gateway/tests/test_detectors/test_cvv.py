"""Tests for the CVV/CVC detector."""

import pytest

from detectors.cvv import CvvDetector


@pytest.fixture
def detector():
    return CvvDetector()


class TestTruePositives:
    def test_cvv_with_space(self, detector):
        matches = detector.detect("CVV 123")
        assert len(matches) == 1
        assert matches[0].match_type == "cvv_3_digit"
        assert matches[0].severity == "high"

    def test_cvv_with_colon(self, detector):
        matches = detector.detect("CVV: 456")
        assert len(matches) == 1

    def test_cvc_with_equals(self, detector):
        matches = detector.detect("CVC=789")
        assert len(matches) == 1

    def test_four_digit_security_code(self, detector):
        matches = detector.detect("security code 1234")
        assert len(matches) == 1
        assert matches[0].match_type == "cvv_4_digit"


class TestMasking:
    def test_raw_cvv_not_logged(self, detector):
        matches = detector.detect("CVV 123")
        assert matches
        assert matches[0].masked_value == "***"

    def test_four_digit_value_masked(self, detector):
        matches = detector.detect("security code 1234")
        assert matches
        assert matches[0].masked_value == "****"


class TestFalsePositives:
    def test_random_three_digit_number_not_detected(self, detector):
        matches = detector.detect("Room number 123")
        assert not matches

    def test_year_not_detected(self, detector):
        matches = detector.detect("The year is 2026")
        assert not matches

    def test_bus_number_not_detected(self, detector):
        matches = detector.detect("Take bus 456")
        assert not matches

    def test_number_without_security_label_not_detected(self, detector):
        matches = detector.detect("The code is 999")
        assert not matches