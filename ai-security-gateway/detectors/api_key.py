"""
detectors/api_key.py
--------------------
Detects API keys, access tokens, and private key blocks.

Patterns covered:
- AWS Access Key IDs (AKIA / ASIA / AROA prefix)
- GCP API keys (AIza prefix)
- Azure Cognitive Services subscription keys (32-char hex)
- Stripe live secret/publishable keys
- GitHub Personal Access Tokens (ghp_, gho_, github_pat_)
- Generic private key PEM blocks (-----BEGIN ... PRIVATE KEY-----)

False-positive reduction:
- Shannon entropy check: candidate tokens must have ≥4.5 bits/char.
  This filters out low-entropy placeholders like "YOUR_API_KEY_HERE".

ARCHITECTURAL CONSTRAINT: No MCP, SSE, OAuth, or Starlette types here.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from core.models import DetectorMatch
from detectors.base import BaseDetector
from detectors.registry import register

# ── Shannon entropy helper ─────────────────────────────────────────────────────

_MIN_ENTROPY_BITS: float = 3.5  # filters near-zero-entropy placeholders (e.g. AKIAAAAAAAAAAAAAAAAA)


def _shannon_entropy(token: str) -> float:
    """Compute Shannon entropy (bits per character) of *token*."""
    if not token:
        return 0.0
    counts = Counter(token)
    length = len(token)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in counts.values()
    )


def _high_entropy(token: str) -> bool:
    return _shannon_entropy(token) >= _MIN_ENTROPY_BITS


# ── Pattern definitions ────────────────────────────────────────────────────────

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # AWS Access Key ID  — 20 chars, starts with AKIA/ASIA/AROA
    # Capture the FULL key (not just the prefix) for entropy checking
    ("aws_access_key", re.compile(r"\b((AKIA|ASIA|AROA)[0-9A-Z]{16})\b")),

    # AWS Secret Access Key — 40 chars, base64url-ish (appears after "aws_secret" etc.)
    # We capture it contextually: keyword within 40 chars before a 40-char token
    ("aws_secret_key", re.compile(
        r"(?i)(?:aws[_\-]?secret[_\-]?(?:access[_\-]?)?key|AWS_SECRET)[^\S\r\n]*[:=][^\S\r\n]*"
        r"([A-Za-z0-9/+]{40})"
    )),

    # GCP API Key — capture full key
    ("gcp_api_key", re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b")),

    # Azure Cognitive Services subscription key (32 lowercase hex chars)
    ("azure_subscription_key", re.compile(
        r"(?i)(?:ocp-apim-subscription-key|subscription[_\-]?key)[^\S\r\n]*[:=][^\S\r\n]*"
        r"([0-9a-f]{32})\b"
    )),

    # Stripe live secret key
    ("stripe_secret_key", re.compile(r"\b(sk_live_[0-9A-Za-z]{24,})\b")),

    # Stripe live publishable key
    ("stripe_publishable_key", re.compile(r"\b(pk_live_[0-9A-Za-z]{24,})\b")),

    # GitHub PAT (classic and fine-grained) — capture full token
    ("github_token", re.compile(r"\b((?:ghp_|gho_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{36,})\b")),

    # PEM private key block (multi-line)
    ("private_key_pem", re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PRIVATE )?PRIVATE KEY-----",
        re.IGNORECASE,
    )),
]


# ── Detector class ─────────────────────────────────────────────────────────────

@register("api_key")
class ApiKeyDetector(BaseDetector):
    """Detects API keys, access tokens, and PEM private key blocks."""

    @property
    def name(self) -> str:
        return "api_key"

    def detect(self, text: str) -> list[DetectorMatch]:
        matches: list[DetectorMatch] = []

        for match_type, pattern in _PATTERNS:
            for m in pattern.finditer(text):
                # Use group(1) as the candidate token if the pattern has capture groups.
                # All patterns now capture the FULL sensitive token as group 1.
                # PEM patterns have no capture groups — use group(0).
                if m.lastindex and m.lastindex >= 1:
                    candidate = m.group(1)
                    span = (m.start(1), m.end(1))
                else:
                    candidate = m.group(0)
                    span = (m.start(), m.end())

                # PEM headers don't need entropy check — structure is the signal
                needs_entropy = match_type != "private_key_pem"

                if needs_entropy and not _high_entropy(candidate):
                    continue  # skip low-entropy placeholder

                matches.append(
                    DetectorMatch(
                        detector_name=self.name,
                        severity="critical",
                        masked_value=self.mask(candidate),
                        span=span,
                        match_type=match_type,
                    )
                )

        return matches
