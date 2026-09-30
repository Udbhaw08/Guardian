"""
detectors/document_utils/pdf_prompt_injection.py
--------------------------------------------------
PDF scanning pipeline for hidden prompt injection detection.

Pipeline:
  1. Open the PDF with PyMuPDF (fitz).
  2. For each page, extract all text spans with full metadata
     (font size, color, opacity, bounding box, page position).
  3. Run stealth_rules checks on each span to detect visually hidden text.
  4. Concatenate all extracted text and run the ML classifier.
  5. Combine stealth flags + ML confidence into a structured DocumentScanResult.

THREAT MODEL:
  Attackers embed prompt injection instructions using:
  - Extremely small fonts (< 4pt)
  - White text on white background
  - Near-zero opacity (transparent) text
  - Off-page / overlapping text placements
  - Hidden OCR-readable layers over scanned images

ARCHITECTURAL CONSTRAINT: No MCP, SSE, or transport types here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    import fitz  # PyMuPDF
    _PYMUPDF_AVAILABLE = True
except ImportError:
    _PYMUPDF_AVAILABLE = False

from detectors.document_utils.classifier import classify_text
from detectors.document_utils.stealth_rules import (
    StealthCheckResult,
    aggregate_stealth_results,
    check_stealth_flags,
)


# ── Result model ──────────────────────────────────────────────────────────────

@dataclass
class DocumentScanResult:
    """
    The complete result of scanning a document for prompt injection.
    Returned by both scan_pdf() and scan_image().
    """
    # Decision fields
    decision: str = "ALLOW"        # "ALLOW" | "WARN_CONFIRM" | "BLOCK"
    severity: str = "low"          # The highest severity found
    reason: str = ""               # Human-readable explanation
    confidence: float = 0.0        # ML model confidence (0.0 – 1.0)

    # Detection details
    stealth_flags: list[str] = field(default_factory=list)
    extracted_text_length: int = 0
    page_count: int = 0

    # Source
    detector_name: str = "pdf_prompt_injection"
    match_type: str = ""


def _decide(
    ml_injection: bool,
    ml_confidence: float,
    stealth: StealthCheckResult,
) -> tuple[str, str, str, str]:
    """
    Combine ML classification and stealth rules to produce a final decision.

    Decision matrix:
    ┌──────────────────┬───────────────────────────────┬──────────────┐
    │ ML predicts inj. │ Stealth flags?                 │ Decision     │
    ├──────────────────┼───────────────────────────────┼──────────────┤
    │ Yes              │ Any                            │ BLOCK        │
    │ No               │ critical (white_on_white etc.) │ BLOCK        │
    │ No               │ high (tiny_font, off_page)     │ WARN_CONFIRM │
    │ No               │ None                           │ ALLOW        │
    └──────────────────┴───────────────────────────────┴──────────────┘

    Returns:
        (decision, severity, reason, match_type)
    """
    severity_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    if ml_injection:
        reason = (
            f"ML model detected prompt injection content "
            f"(confidence: {ml_confidence:.0%})."
        )
        if stealth.is_suspicious:
            reason += f" Additionally, hidden text flags were detected: {stealth.flags}."
        sev = "critical" if ml_confidence > 0.85 else "high"
        return "BLOCK", sev, reason, "ml_injection"

    if stealth.is_suspicious:
        if severity_rank.get(stealth.severity, 0) >= severity_rank["critical"]:
            reason = (
                f"Critically hidden text detected ({stealth.flags}). "
                "This text is not visible to human readers but is readable by AI. "
                "Blocking as a precaution even though ML model did not flag content."
            )
            return "BLOCK", "critical", reason, "hidden_text"
        else:
            reason = (
                f"Suspicious hidden text metadata found ({stealth.flags}). "
                "The document may contain concealed content. Please review before proceeding."
            )
            return "WARN_CONFIRM", stealth.severity, reason, "suspicious_metadata"

    return "ALLOW", "low", "No prompt injection or hidden text detected.", ""


# ── Main scanner ──────────────────────────────────────────────────────────────

def scan_pdf(pdf_bytes: bytes) -> DocumentScanResult:
    """
    Scan a PDF document for hidden prompt injection.

    Args:
        pdf_bytes: Raw bytes of the PDF file.

    Returns:
        DocumentScanResult with decision, confidence, stealth_flags, and reason.

    Raises:
        ImportError: If PyMuPDF is not installed.
        ValueError: If the bytes are not a valid PDF.
    """
    if not _PYMUPDF_AVAILABLE:
        raise ImportError(
            "PyMuPDF is required for PDF scanning. "
            "Install it with: pip install pymupdf"
        )

    # ── 1. Open the PDF from bytes ────────────────────────────────────────────
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Failed to parse PDF: {exc}") from exc

    page_count = doc.page_count
    all_text_parts: list[str] = []
    all_stealth_results: list[StealthCheckResult] = []

    # ── 2. Extract text spans from every page ─────────────────────────────────
    for page_index in range(page_count):
        page = doc.load_page(page_index)
        page_rect = tuple(page.rect)  # (x0, y0, x1, y1)

        # get_text("dict") gives per-span metadata: font size, color, bbox
        # Note: "dict" mode is more compatible across PyMuPDF versions than "rawdict"
        raw_dict: dict[str, Any] = page.get_text("dict")

        for block in raw_dict.get("blocks", []):
            if block.get("type") != 0:  # type 0 = text block
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    span_text = span.get("text", "").strip()
                    if not span_text:
                        continue

                    # Collect all text (visible or not) for ML classification
                    all_text_parts.append(span_text)

                    # Check for stealth indicators in this span's metadata
                    stealth_result = check_stealth_flags(span, page_rect=page_rect)
                    if stealth_result.is_suspicious:
                        all_stealth_results.append(stealth_result)

    doc.close()

    # ── 3. Aggregate results ──────────────────────────────────────────────────
    full_text = " ".join(all_text_parts)
    aggregate_stealth = aggregate_stealth_results(all_stealth_results)

    # ── 4. ML classification on full extracted text ───────────────────────────
    ml_injection, ml_confidence = classify_text(full_text)

    # ── 5. Final decision ─────────────────────────────────────────────────────
    decision, severity, reason, match_type = _decide(
        ml_injection, ml_confidence, aggregate_stealth
    )

    return DocumentScanResult(
        decision=decision,
        severity=severity,
        reason=reason,
        confidence=ml_confidence,
        stealth_flags=aggregate_stealth.flags,
        extracted_text_length=len(full_text),
        page_count=page_count,
        detector_name="pdf_prompt_injection",
        match_type=match_type,
    )
