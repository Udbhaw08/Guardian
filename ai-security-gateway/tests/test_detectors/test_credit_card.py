"""Tests for the credit card detector."""

import pytest

from detectors.credit_card import CreditCardDetector


@pytest.fixture
def detector():
    return CreditCardDetector()


class TestTruePositives:
    def test_visa_card_luhn_valid(self, detector):
        # Standard Luhn-valid Visa test number
        matches = detector.detect("Charge 4111111111111111 please")
        assert len(matches) == 1
        assert matches[0].match_type == "visa"
        assert matches[0].severity == "high"

    def test_mastercard_luhn_valid(self, detector):
        matches = detector.detect("Card: 5500005555555559")
        assert any(m.match_type == "mastercard" for m in matches)

    def test_amex_15_digit(self, detector):
        matches = detector.detect("amex: 378282246310005")
        assert any(m.match_type == "amex" for m in matches)

    def test_discover_card(self, detector):
        matches = detector.detect("card: 6011111111111117")
        assert any(m.match_type == "discover" for m in matches)

    def test_spaced_card_number(self, detector):
        matches = detector.detect("4111 1111 1111 1111")
        assert len(matches) == 1

    def test_dashed_card_number(self, detector):
        matches = detector.detect("4111-1111-1111-1111")
        assert len(matches) == 1


class TestMasking:
    def test_raw_cc_not_in_masked_value(self, detector):
        card = "4111111111111111"
        matches = detector.detect(card)
        assert matches
        assert card not in matches[0].masked_value
        assert "****" in matches[0].masked_value

    def test_first_four_visible(self, detector):
        matches = detector.detect("4111111111111111")
        assert matches
        assert matches[0].masked_value.startswith("4111")


class TestFalsePositives:
    def test_luhn_invalid_number_rejected(self, detector):
        # 4111111111111112 fails Luhn (last digit changed)
        matches = detector.detect("Invalid: 4111111111111112")
        assert not matches, "Luhn-invalid number should be rejected"

    def test_short_number_not_matched(self, detector):
        matches = detector.detect("Reference: 123456789012")  # 12 digits
        assert not matches

    def test_normal_text_not_matched(self, detector):
        matches = detector.detect("The order total is $50.00 for 2 items")
        assert not matches
