"""
detectors/injection_rules.py
------------------------------
High-precision, deliberately narrow regex rules for known prompt injection templates.

IMPORTANT DESIGN PRINCIPLE:
    Rules are SIGNALS, not arbiters. They contribute a score (0.0–1.0) to
    the confidence aggregator. They do NOT make the final blocking decision.

    Rules here should ONLY cover verbatim attack templates that almost never
    appear in legitimate text. Broad patterns like "ignore.*instructions" or
    "pretend.*no restrictions" must NOT be rules because they produce false positives.

    When in doubt, do NOT add a rule. The ML model + verifier handle nuanced cases.

Usage:
    from detectors.injection_rules import evaluate_rules
    matches = evaluate_rules(text)
    # matches is a list of (rule_name, contribution_score) tuples
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RuleMatch:
    """A single rule that fired on the input text."""
    rule_name: str
    contribution: float    # 0.0–1.0: how much this rule boosts the confidence score
    matched_snippet: str   # short excerpt of matched text (for logging only)


# ── Rule definitions ───────────────────────────────────────────────────────────
# Each rule is a tuple: (name, compiled_pattern, contribution_score)
#
# Contribution scoring:
#   1.0 — virtually never appears in legitimate text (unambiguous attack template)
#   0.8 — very rarely legitimate, almost always an attack
#   0.6 — somewhat specific but could rarely appear legitimately
#
# These are VERBATIM or near-verbatim known attack patterns from real jailbreak datasets.
# See: https://github.com/verazuo/jailbreak_llms for reference patterns.

_RULES: list[tuple[str, re.Pattern, float]] = [
    # Classic verbatim injection templates — score 1.0
    (
        "ignore_all_previous_instructions",
        re.compile(r"ignore\s+all\s+previous\s+instructions", re.IGNORECASE),
        1.0,
    ),
    (
        "ignore_all_prior_instructions",
        re.compile(r"ignore\s+all\s+prior\s+instructions", re.IGNORECASE),
        1.0,
    ),
    (
        "disregard_system_prompt",
        re.compile(r"disregard\s+(your\s+)?(system\s+prompt|safety\s+guidelines|previous\s+instructions)", re.IGNORECASE),
        1.0,
    ),
    (
        "forget_previous_instructions",
        re.compile(r"forget\s+(all\s+)?(your\s+)?(previous|prior|earlier)\s+(instructions|guidelines|rules)", re.IGNORECASE),
        1.0,
    ),

    # Specific jailbreak persona names — score 1.0
    (
        "jailbreak_dan",
        re.compile(r"\b(act\s+as|you\s+are(\s+now)?|pretend\s+to\s+be)\s+DAN\b|\bdo\s+anything\s+now\b", re.IGNORECASE),
        1.0,
    ),
    (
        "jailbreak_developer_mode",
        re.compile(r"developer\s+mode\s+(enabled|activated|unlocked)", re.IGNORECASE),
        1.0,
    ),

    # Fake system / admin prefix injection — score 0.9
    # These patterns simulate LLM system prompt formatting to confuse the model
    (
        "fake_system_prefix",
        re.compile(r"(\[SYSTEM\]|\<system\>|\[ADMIN\]|\[INST\])\s*:", re.IGNORECASE),
        0.9,
    ),
    (
        "new_instructions_override",
        re.compile(r"(new|updated|revised)\s+instructions?\s*:\s*\n", re.IGNORECASE),
        0.85,
    ),

    # All-caps verbatim templates (common in automated attacks) — score 0.9
    (
        "caps_ignore_everything",
        re.compile(r"IGNORE\s+(EVERYTHING|ALL\s+PREVIOUS|ALL\s+PRIOR)\s+(ABOVE|INSTRUCTIONS|RULES)", re.IGNORECASE),
        0.9,
    ),

    # Unicode homoglyph obfuscation — score 0.8
    # Attackers substitute lookalike characters: Cyrillic 'е' for Latin 'e', etc.
    (
        "unicode_homoglyph",
        re.compile(r"[іеаоркхуcорсе]\w{2,}\s+(аll|рrеviоus|рriоr|instructions)", re.UNICODE),
        0.8,
    ),

    # Leet-speak obfuscation — score 0.8
    (
        "leetspeak_obfuscation",
        re.compile(r"\b(1gn0re|1gnore|ign0re|0verride|0v3rride|1nstruct10ns)\b", re.IGNORECASE),
        0.8,
    ),
]


def evaluate_rules(text: str) -> list[RuleMatch]:
    """
    Apply all rules to the input text.

    Args:
        text: The raw input text to scan.

    Returns:
        List of RuleMatch objects for every rule that fired.
        Empty list means no rules matched (text may still be an injection
        caught by the ML classifier or verifier).
    """
    matches: list[RuleMatch] = []
    for rule_name, pattern, contribution in _RULES:
        m = pattern.search(text)
        if m:
            # Capture a safe, non-sensitive snippet for logging
            start = max(0, m.start() - 10)
            end = min(len(text), m.end() + 10)
            snippet = text[start:end].replace("\n", " ").strip()
            matches.append(RuleMatch(
                rule_name=rule_name,
                contribution=contribution,
                matched_snippet=snippet[:60],   # cap at 60 chars for log safety
            ))
    return matches


def get_rule_score(rule_matches: list[RuleMatch]) -> float:
    """
    Aggregate multiple rule matches into a single [0, 1] score.

    If multiple rules fire, take the maximum contribution (not the sum),
    to avoid runaway scores when multiple rules overlap on the same attack.

    Args:
        rule_matches: Output of evaluate_rules().

    Returns:
        Single float in [0.0, 1.0]. 0.0 means no rules fired.
    """
    if not rule_matches:
        return 0.0
    return max(m.contribution for m in rule_matches)
