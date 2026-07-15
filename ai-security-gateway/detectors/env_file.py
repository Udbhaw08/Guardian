"""
detectors/env_file.py
---------------------
Detects environment/secrets file patterns in text.

Patterns covered:
  1. Sensitive env variable assignments (SECRET_KEY=..., DATABASE_URL=..., etc.)
  2. File path references to .env or env.example files in text
  3. Multiple KEY=VALUE lines that indicate a pasted .env file

ARCHITECTURAL CONSTRAINT: No MCP, SSE, OAuth, or Starlette types here.
"""

from __future__ import annotations

import re

from core.models import DetectorMatch
from detectors.base import BaseDetector
from detectors.registry import register

# ── Sensitive env variable name patterns ──────────────────────────────────────
# Matches common secret/credential env vars assigned with = or :
_SECRET_VAR_PATTERN = re.compile(
    r"""(?ix)
    (?:^|[\n\r])                            # start of line
    [ \t]*                                  # optional leading whitespace
    (?:export[ \t]+)?                       # optional 'export' keyword
    (?:
        # Credential / secret variable names
        (?:secret[_-]?key|api[_-]?key|api[_-]?secret|access[_-]?token|
           auth[_-]?token|jwt[_-]?secret|session[_-]?secret|
           private[_-]?key|client[_-]?secret|app[_-]?secret|
           # Database
           database[_-]?url|db[_-]?(?:url|password|pass|pwd)|
           postgres(?:ql)?[_-]?url|mysql[_-]?url|mongodb[_-]?uri|
           # Cloud / infra
           aws[_-]?access[_-]?key|aws[_-]?secret|
           gcp[_-]?key|azure[_-]?key|
           # Auth
           oauth[_-]?(?:token|secret)|encryption[_-]?key|
           # Generic sensitive
           password|passwd|pwd|token|secret|credential
        )
    )
    [ \t]*[=:][ \t]*         # separator
    (?!\s*(?:your[_-]?|example|xxx|placeholder|changeme|change.me|none|null|true|false|$))
    \S+                      # non-empty value (not just whitespace)
    """,
    re.IGNORECASE | re.MULTILINE,
)

# ── Env file path reference patterns ─────────────────────────────────────────
# Catches when a .env filename is mentioned in text (e.g. ZIP listing output)
_ENV_FILE_PATH_PATTERN = re.compile(
    r"""(?ix)
    (?:^|[\s/\\,;(])                        # start of word
    (?:[a-z0-9_\-./\\]*/)?                  # optional path prefix
    (?:
        \.env(?:\.[a-z]+)?                  # .env, .env.local, .env.production
        | env(?:\.[a-z]+)                   # env.example, env.local (bare, must have extension)
        | \.envrc
        | secrets\.env
        | config\.env
    )
    (?=[\s,;)\n\r]|$)                       # end of word
    """,
    re.MULTILINE,
)

# ── Bulk KEY=VALUE pattern ────────────────────────────────────────────────────
# ≥3 KEY=VALUE lines in the same text → likely a pasted .env file
_KV_LINE_PATTERN = re.compile(
    r"^[ \t]*[A-Z][A-Z0-9_]{2,}[ \t]*=[ \t]*\S+",
    re.MULTILINE,
)


@register("env_file")
class EnvFileDetector(BaseDetector):
    """Detects environment file contents and .env file path references."""

    @property
    def name(self) -> str:
        return "env_file"

    def detect(self, text: str) -> list[DetectorMatch]:
        matches: list[DetectorMatch] = []
        seen_spans: set[tuple[int, int]] = set()

        # ── 1. Sensitive variable assignments ─────────────────────────────────
        for m in _SECRET_VAR_PATTERN.finditer(text):
            span = (m.start(), m.end())
            if span not in seen_spans:
                seen_spans.add(span)
                raw = m.group(0).strip()
                matches.append(
                    DetectorMatch(
                        detector_name=self.name,
                        severity="critical",
                        masked_value=self.mask(raw, visible_prefix=8),
                        span=span,
                        match_type="secret_env_var",
                    )
                )

        # ── 2. .env file path references in text ──────────────────────────────
        for m in _ENV_FILE_PATH_PATTERN.finditer(text):
            raw = m.group(0).strip()
            span = (m.start(), m.end())
            if span not in seen_spans:
                seen_spans.add(span)
                matches.append(
                    DetectorMatch(
                        detector_name=self.name,
                        severity="high",
                        masked_value=raw,          # keep filename visible — it's not secret itself
                        span=span,
                        match_type="env_file_path",
                    )
                )

        # ── 3. Bulk KEY=VALUE lines (pasted .env file heuristic) ─────────────
        kv_lines = _KV_LINE_PATTERN.findall(text)
        if len(kv_lines) >= 3 and not matches:
            # Many UPPER_CASE=value lines — likely a full .env file pasted
            matches.append(
                DetectorMatch(
                    detector_name=self.name,
                    severity="high",
                    masked_value=f"<ENV_FILE_CONTENT {len(kv_lines)} vars>",
                    span=(0, len(text)),
                    match_type="env_file_content",
                )
            )

        return matches
