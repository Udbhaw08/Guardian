"""
detectors/document_utils/zip_scanner.py
-----------------------------------------
Scans a ZIP archive for sensitive files before it is processed.

Primary threat:  Developers accidentally upload project ZIPs that contain
                 .env files with API keys, database passwords, and secrets.

Detection logic:
  - Lists all entries inside the ZIP without extracting them.
  - Checks each filename against a set of sensitive patterns.
  - Returns a severity level based on what was found.

Severity rules:
  CRITICAL  ->  .env found at the root level (e.g., ".env", ".env.production")
  HIGH      ->  .env found nested inside subdirectories (e.g., "backend/.env")
  LOW       ->  No sensitive files found.

No new pip packages required. Uses Python's built-in zipfile module.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field

# ── Patterns that indicate a sensitive env file ────────────────────────────────

_SENSITIVE_NAMES: frozenset[str] = frozenset({
    # dotfile variants
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.staging",
    ".env.test",
    ".env.example",
    ".env.backup",
    ".envrc",
    # bare-name variants (no leading dot)
    "env",
    "env.example",
    "env.local",
    "env.production",
    "env.development",
    "env.staging",
    "env.test",
    "env.backup",
    # explicit secrets files
    "secrets.env",
    "config.env",
    ".secrets",
    "secrets",
})


def _is_sensitive(filename: str) -> bool:
    """Return True if this ZIP entry path contains a sensitive env file."""
    name = filename.strip("/").lower()
    basename = name.rsplit("/", 1)[-1]

    # Exact match against known sensitive names
    if basename in _SENSITIVE_NAMES:
        return True

    # Catch any file starting with ".env" (e.g. .env.prod.bak)
    if basename.startswith(".env"):
        return True

    # Catch any bare name starting with "env." (e.g. env.example, env.prod)
    if basename.startswith("env."):
        return True

    return False


@dataclass
class ZipScanResult:
    decision: str
    severity: str
    reason: str
    sensitive_files: list[str] = field(default_factory=list)
    all_files: list[str] = field(default_factory=list)
    file_count: int = 0
    detector_name: str = "zip_env_leak"


def scan_zip(zip_bytes: bytes) -> ZipScanResult:
    """
    Scan a ZIP archive for .env files and other sensitive env configs.

    Args:
        zip_bytes: Raw bytes of the ZIP file.

    Returns:
        ZipScanResult with decision, severity, and list of offending files.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        return ZipScanResult(
            decision="BLOCK",
            severity="high",
            reason="The uploaded file is not a valid ZIP archive or is corrupted.",
        )
    except Exception as exc:
        return ZipScanResult(
            decision="BLOCK",
            severity="high",
            reason=f"Could not open ZIP file: {exc}",
        )

    all_names = [info.filename for info in zf.infolist() if not info.is_dir()]
    zf.close()

    sensitive: list[str] = [f for f in all_names if _is_sensitive(f)]

    if not sensitive:
        return ZipScanResult(
            decision="ALLOW",
            severity="low",
            reason=f"ZIP archive is clean. Scanned {len(all_names)} file(s). No sensitive env files found.",
            sensitive_files=[],
            all_files=all_names,
            file_count=len(all_names),
        )

    # Root-level .env files are more critical than nested ones
    root_level = [f for f in sensitive if "/" not in f.strip("/")]
    if root_level:
        severity = "critical"
        reason = (
            f"CRITICAL: Root-level .env file(s) detected inside ZIP: {root_level}. "
            f"This file likely contains plaintext secrets (API keys, passwords, tokens). "
            f"Remove it before sharing or uploading."
        )
    else:
        severity = "high"
        reason = (
            f"HIGH: Sensitive env file(s) found inside ZIP subdirectories: {sensitive}. "
            f"These files may contain credentials or secrets."
        )

    return ZipScanResult(
        decision="BLOCK",
        severity=severity,
        reason=reason,
        sensitive_files=sensitive,
        all_files=all_names,
        file_count=len(all_names),
    )
