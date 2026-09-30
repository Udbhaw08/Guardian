"""
detectors/verifier.py
---------------------
Context Verifier — Stage 3 of the prompt injection detection pipeline.

The verifier understands INTENT, not just surface patterns. It cross-checks
the raw ML probability score by looking for contextual signals that indicate
whether a prompt is genuinely malicious or legitimately using injection-surface words.

OUTPUT: A single float adjustment in [-0.50, +0.40].
  - Negative → text has legitimate intent signals → reduce confidence score
  - Positive → text has attack-confirming signals → boost confidence score
  - 0.0      → neutral / no clear context signals

IMPORTANT: The verifier does NOT make a blocking decision.
It outputs one float that the aggregator weighs with other signals.

This is where the "pretend as a teacher" problem is solved:
  → Educational context signals detected → adjustment ≈ -0.35
  → Combined with ML score ~0.35 and rule score ~0.70:
     final_confidence = 0.35*0.70 + 0.45*0.35 + 0.20*(-0.35) = 0.313 → ALLOW
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class VerifierResult:
    """Output from the context verifier."""
    adjustment: float                       # net float adjustment to confidence
    signals_reducing: list[str] = field(default_factory=list)   # legitimate context found
    signals_boosting: list[str] = field(default_factory=list)   # attack context found


# ── Legitimate context signals (reduce confidence) ────────────────────────────

# Educational & tutoring domain
_EDU_KEYWORDS = re.compile(
    r"\b(dsa|algorithm|data\s+structure|explain|tutorial|teach|concept|"
    r"recursion|sorting|searching|binary\s+search|linked\s+list|binary\s+tree|"
    r"graph|traversal|dynamic\s+programming|greedy|two\s+pointer|sliding\s+window|"
    r"complexity|time\s+complexity|space\s+complexity|big\s+o|backtracking|"
    r"hashmap|stack|queue|heap|trie|segment\s+tree)\b",
    re.IGNORECASE,
)

# Programming / engineering domain
_CODE_KEYWORDS = re.compile(
    r"\b(function|variable|class|method|object|bug|error|exception|syntax|"
    r"compile|runtime|debug|refactor|import|module|library|framework|api|"
    r"database|sql|query|loop|iteration|recursion|lambda|closure|decorator|"
    r"inheritance|polymorphism|encapsulation|abstract|interface|pytest|unittest|"
    r"docker|kubernetes|git|commit|merge|pull\s+request|branch|deploy|"
    r"def\s+\w+|class\s+\w+|import\s+\w+|from\s+\w+\s+import|return\s+\w+)\b",
    re.IGNORECASE,
)

# Question / help-seeking phrasing (starts or ends with question markers)
_QUESTION_START = re.compile(
    r"^(how|what|why|when|where|who|can\s+you|could\s+you|please|help\s+me|"
    r"explain|tell\s+me|describe|show\s+me|what\s+is|what\s+are|is\s+it|"
    r"should\s+i|would\s+you)\b",
    re.IGNORECASE,
)
_QUESTION_END = re.compile(r"\?\s*$")

# Financial / invoice document context
_FINANCIAL_KEYWORDS = re.compile(
    r"\b(invoice|amount|total|due|payment|gstin|pan|tax|gst|billing|"
    r"purchase\s+order|receipt|payable|balance|bank|account|ifsc|swift|"
    r"wire\s+transfer|net\s+30|late\s+fee|subtotal|vat|usd|inr|eur)\b",
    re.IGNORECASE,
)

# Creative / storytelling context (roleplay is fine, attacks are not)
_CREATIVE_KEYWORDS = re.compile(
    r"\b(story|novel|fiction|character|plot|narrative|scene|chapter|"
    r"write\s+a|create\s+a|help\s+me\s+write|creative\s+writing|"
    r"brainstorm|worldbuilding|protagonist|antagonist|dialogue)\b",
    re.IGNORECASE,
)

# Teaching role phrasing (benign: "pretend as a teacher", "act as a professor")
_TEACHING_ROLE = re.compile(
    r"\b(as\s+a\s+teacher|as\s+a\s+professor|as\s+a\s+tutor|as\s+a\s+mentor|"
    r"as\s+a\s+senior\s+engineer|as\s+a\s+developer|as\s+an\s+instructor|"
    r"as\s+a\s+coach|as\s+an\s+expert|as\s+a\s+consultant)\b",
    re.IGNORECASE,
)

# ── Attack-confirming signals (boost confidence) ──────────────────────────────

# Harmful domain keywords (strongly indicates malicious intent)
_HARMFUL_KEYWORDS = re.compile(
    r"\b(bomb|weapon|explosive|poison|hack\s+into|malware|ransomware|"
    r"steal\s+(data|credentials|password)|social\s+engineering|phishing|"
    r"child\s+(abuse|exploitation|pornography)|bypass\s+(security|filter|safety)|"
    r"make\s+(a\s+)?(bomb|weapon|drug)|synthesize\s+\w+\s+(drug|poison))\b",
    re.IGNORECASE,
)

# Fake system prefix injection (attackers simulate LLM prompt formatting)
_FAKE_SYSTEM = re.compile(
    r"(\[SYSTEM\]|\[ADMIN\]|\[INST\]|\<\|system\|\>|\<system\>)\s*:",
    re.IGNORECASE,
)

# Unicode homoglyph substitution (Cyrillic/Greek chars replacing Latin)
# Checks for unusual Unicode character ranges mixed into otherwise-ASCII words
_UNICODE_SUSPICIOUS = re.compile(
    r"[а-яёА-ЯЁ\u0370-\u03FF\u2000-\u206F]{1,3}[a-zA-Z]{2,}|"  # Cyrillic/Greek mixed in
    r"[a-zA-Z]{2,}[а-яёА-ЯЁ\u0370-\u03FF]{1,3}",
    re.UNICODE,
)

# Leet-speak injection obfuscation
_LEETSPEAK = re.compile(
    r"\b(1gn0r3?|1gnore|ign0re|0verr?ide|0v3rride|1nstruct|!nstruct|"
    r"d1sr3gard|d1sregard)\b",
    re.IGNORECASE,
)

# Excessive whitespace padding (attacker trick to break regex patterns)
_WHITESPACE_PADDING = re.compile(r"i\s{3,}g\s{3,}n\s{3,}o\s{3,}r\s{3,}e", re.IGNORECASE)


def verify(text: str, ml_score: float) -> VerifierResult:
    """
    Analyse the text for contextual intent signals.

    The verifier is most useful when the ML score is in the uncertain range
    (0.30–0.80). At very high ML scores (>0.90) or very low (<0.10), context
    signals have less impact because the ML model is already highly confident.

    Args:
        text:      The raw input text.
        ml_score:  The ML classifier's predict_proba score for class 1 (injection).

    Returns:
        VerifierResult with net adjustment and signal lists for logging.
    """
    text_lower = text.lower()
    reducing: list[str] = []
    boosting: list[str] = []
    net_adjustment = 0.0

    # ── Legitimate context signals ─────────────────────────────────────────────

    if _EDU_KEYWORDS.search(text):
        reducing.append("educational_domain")
        net_adjustment -= 0.30

    if _CODE_KEYWORDS.search(text):
        reducing.append("programming_context")
        net_adjustment -= 0.25

    if _TEACHING_ROLE.search(text):
        reducing.append("teaching_role_framing")
        net_adjustment -= 0.20

    if _QUESTION_START.match(text.strip()) or _QUESTION_END.search(text):
        reducing.append("question_phrasing")
        net_adjustment -= 0.20

    if _FINANCIAL_KEYWORDS.search(text):
        reducing.append("financial_document_context")
        net_adjustment -= 0.20

    if _CREATIVE_KEYWORDS.search(text) and not _HARMFUL_KEYWORDS.search(text):
        reducing.append("creative_writing_context")
        net_adjustment -= 0.15

    # Short text with no imperative structure is unlikely to be an injection
    word_count = len(text.split())
    if word_count < 12 and not _HARMFUL_KEYWORDS.search(text):
        reducing.append("short_benign_query")
        net_adjustment -= 0.15

    # ── Attack-confirming signals ──────────────────────────────────────────────

    if _HARMFUL_KEYWORDS.search(text):
        boosting.append("harmful_domain_keywords")
        net_adjustment += 0.40
        # Cancel any educational reductions — harmful domain trumps context
        if "educational_domain" in reducing or "teaching_role_framing" in reducing:
            net_adjustment += 0.20   # partial cancel of the reduction

    if _FAKE_SYSTEM.search(text):
        boosting.append("fake_system_prefix")
        net_adjustment += 0.35

    if _UNICODE_SUSPICIOUS.search(text):
        boosting.append("unicode_homoglyph_obfuscation")
        net_adjustment += 0.30

    if _LEETSPEAK.search(text):
        boosting.append("leetspeak_obfuscation")
        net_adjustment += 0.25

    if _WHITESPACE_PADDING.search(text):
        boosting.append("whitespace_padding_obfuscation")
        net_adjustment += 0.25

    # ── Dampen adjustment when ML is very certain ─────────────────────────────
    # If the ML model is >0.90 confident, verifier context signals have less say
    # (model likely trained on very similar examples). Scale down reductions.
    if ml_score > 0.90 and net_adjustment < 0:
        net_adjustment *= 0.4   # reduce the dampening effect

    # Clamp to allowed range
    net_adjustment = max(-0.50, min(0.40, net_adjustment))

    return VerifierResult(
        adjustment=round(net_adjustment, 4),
        signals_reducing=reducing,
        signals_boosting=boosting,
    )
