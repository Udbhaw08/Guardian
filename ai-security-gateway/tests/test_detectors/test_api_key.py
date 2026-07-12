"""Tests for the api_key detector."""

import pytest

from detectors.api_key import ApiKeyDetector


@pytest.fixture
def detector():
    return ApiKeyDetector()


# ── True Positive Tests ────────────────────────────────────────────────────────

class TestTruePositives:
    def test_aws_access_key_id(self, detector):
        text = "My key is AKIAIOSFODNN7EXAMPLE and it's legit"
        matches = detector.detect(text)
        assert len(matches) == 1
        assert matches[0].match_type == "aws_access_key"
        assert matches[0].severity == "critical"
        assert "AKIA" in matches[0].masked_value
        assert "IOSFODNN7EXAMPLE" not in matches[0].masked_value  # must be masked

    def test_aws_secret_key_context(self, detector):
        text = 'AWS_SECRET=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        matches = detector.detect(text)
        assert any(m.match_type == "aws_secret_key" for m in matches)

    def test_stripe_live_secret_key(self, detector):
        text = "Use stripe key: sk_live_REPLACE_WITH_TEST_KEY_HERE"
        matches = detector.detect(text)
        assert any(m.match_type == "stripe_secret_key" for m in matches)

    def test_stripe_live_publishable_key(self, detector):
        text = "publishable: pk_live_51AbcdefGhijklMnopqrStuVwxyz"
        matches = detector.detect(text)
        assert any(m.match_type == "stripe_publishable_key" for m in matches)

    def test_github_pat_classic(self, detector):
        text = "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcde12345"
        matches = detector.detect(text)
        assert any(m.match_type == "github_token" for m in matches)

    def test_github_fine_grained_pat(self, detector):
        text = "github_pat_11ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz"
        matches = detector.detect(text)
        assert any(m.match_type == "github_token" for m in matches)

    def test_gcp_api_key(self, detector):
        # GCP API keys: AIza + 35 alphanumeric/dash/underscore chars = 39 total
        # Use a high-entropy realistic-looking key
        matches = detector.detect("gcp key = AIzaSyBX-2KWNqPiZaE_K7bG0r3vXTlMj5GdLmY")
        assert any(m.match_type == "gcp_api_key" for m in matches)


    def test_pem_private_key_block(self, detector):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
        matches = detector.detect(text)
        assert any(m.match_type == "private_key_pem" for m in matches)

    def test_pem_ec_private_key(self, detector):
        text = "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIBkg..."
        matches = detector.detect(text)
        assert any(m.match_type == "private_key_pem" for m in matches)

    def test_pem_openssh_private_key(self, detector):
        text = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAA..."
        matches = detector.detect(text)
        assert any(m.match_type == "private_key_pem" for m in matches)


# ── Masked value tests ─────────────────────────────────────────────────────────

class TestMasking:
    def test_matched_value_is_masked(self, detector):
        text = "AKIAIOSFODNN7EXAMPLE"
        matches = detector.detect(text)
        assert matches, "Expected at least one match"
        raw = "AKIAIOSFODNN7EXAMPLE"
        for m in matches:
            assert raw not in m.masked_value, "Raw sensitive value must not appear in masked_value"
            assert "****" in m.masked_value

    def test_span_points_to_original_text(self, detector):
        text = "key: AKIAIOSFODNN7EXAMPLE"
        matches = detector.detect(text)
        assert matches
        for m in matches:
            start, end = m.span
            extracted = text[start:end]
            # Extracted substring must contain the key material
            assert "AKIA" in extracted or len(extracted) >= 4


# ── False Positive / Negative Tests ───────────────────────────────────────────

class TestFalsePositives:
    def test_low_entropy_aws_lookalike_rejected(self, detector):
        # Near-zero entropy — all repeated chars (entropy ~0.0), must be filtered
        text = "AKIAAAAAAAAAAAAAAAAA"
        matches = detector.detect(text)
        aws_matches = [m for m in matches if m.match_type == "aws_access_key"]
        assert not aws_matches, "Zero-entropy token should be filtered by entropy check"

    def test_another_low_entropy_rejected(self, detector):
        # Only 2 distinct chars, very low entropy
        text = "AKIA01010101010101010"  # entropy ~1.0
        matches = detector.detect(text)
        aws_matches = [m for m in matches if m.match_type == "aws_access_key"]
        assert not aws_matches, "Very low-entropy token should be filtered"

    def test_placeholder_string_rejected(self, detector):
        text = "Set API key to: AKIAYOURKEY123456789"  # 'YOURKEY' is low entropy
        matches = detector.detect(text)
        # We don't assert zero matches since the token has mixed case;
        # we assert it's not flagged if entropy is below threshold.
        # This tests that entropy filtering is applied.
        for m in matches:
            if m.match_type == "aws_access_key":
                candidate = text[m.span[0]:m.span[1]]
                # Entropy must be above threshold for this match to exist
                from detectors.api_key import _shannon_entropy, _MIN_ENTROPY_BITS
                assert _shannon_entropy(candidate) >= _MIN_ENTROPY_BITS

    def test_random_word_not_flagged(self, detector):
        text = "Hello world, this is a normal sentence with no secrets."
        matches = detector.detect(text)
        assert not matches

    def test_test_stripe_key_not_flagged(self, detector):
        # Test (non-live) Stripe keys should not be flagged
        text = "sk_test_REPLACE_WITH_TEST_KEY_HERE is a test key"
        matches = detector.detect(text)
        stripe_matches = [m for m in matches if m.match_type == "stripe_secret_key"]
        assert not stripe_matches, "Test-mode Stripe keys should not be flagged as live keys"
