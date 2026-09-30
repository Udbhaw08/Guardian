"""
detectors/document_utils/image_prompt_injection.py
----------------------------------------------------
Image scanning pipeline for hidden prompt injection via OCR.

Pipeline:
  1. Load the image with Pillow.
  2. Apply contrast enhancement so hidden text (white-on-white,
     low-contrast, light watermarks) becomes readable by OCR.
  3. Run Tesseract OCR to extract all readable text.
  4. Run the ML classifier on the extracted text.
  5. Return a DocumentScanResult.

THREAT MODEL:
  Attackers embed prompt injection instructions in images using:
  - White text on white / near-white backgrounds
  - Light watermarks with injection content
  - Low-contrast text embedded in screenshots
  - Text embedded in metadata or as invisible overlays

NOTE: This module requires:
  - Pillow: pip install Pillow
  - pytesseract: pip install pytesseract
  - Tesseract binary on the system PATH (install from https://github.com/UB-Mannheim/tesseract/wiki)

ARCHITECTURAL CONSTRAINT: No MCP, SSE, or transport types here.
"""

from __future__ import annotations

import io

try:
    from PIL import Image, ImageEnhance, ImageFilter
    _PILLOW_AVAILABLE = True
except ImportError:
    _PILLOW_AVAILABLE = False

try:
    import pytesseract
    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_AVAILABLE = False

from detectors.document_utils.classifier import classify_text
from detectors.document_utils.pdf_prompt_injection import DocumentScanResult, _decide
from detectors.document_utils.stealth_rules import StealthCheckResult


# ── OCR preprocessing ─────────────────────────────────────────────────────────

def _preprocess_for_ocr(image: "Image.Image") -> "Image.Image":
    """
    Apply image enhancements to maximise OCR accuracy on hidden text.

    Steps:
    1. Convert to RGB (handles PNG transparency / palette modes)
    2. Convert to greyscale — removes color distractions
    3. Boost contrast aggressively — surfaces white-on-white and light text
    4. Sharpen — helps OCR detect individual characters more precisely
    5. Scale up if small — Tesseract works better on images >= 300 DPI effective
    """
    # 1. Normalise mode
    img = image.convert("RGB")

    # 2. Greyscale
    img = img.convert("L")

    # 3. High contrast (factor 3.0 surfaces near-invisible text)
    img = ImageEnhance.Contrast(img).enhance(3.0)

    # 4. Sharpen
    img = img.filter(ImageFilter.SHARPEN)

    # 5. Scale up small images
    w, h = img.size
    if w < 1000 or h < 1000:
        scale = max(1000 / w, 1000 / h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    return img


def _extract_text_from_image(image_bytes: bytes) -> tuple[str, str | None]:
    """
    Run OCR on raw image bytes and return extracted text.

    Returns:
        (extracted_text, error_message_or_None)
    """
    if not _PILLOW_AVAILABLE:
        return "", "Pillow is not installed. Run: pip install Pillow"
    if not _TESSERACT_AVAILABLE:
        return "", "pytesseract is not installed. Run: pip install pytesseract"

    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        return "", f"Failed to open image: {exc}"

    try:
        preprocessed = _preprocess_for_ocr(image)
        # PSM 11: Sparse text — finds text anywhere in image, good for hidden text
        config = "--psm 11 --oem 3"
        text = pytesseract.image_to_string(preprocessed, config=config)
        return text.strip(), None
    except pytesseract.TesseractNotFoundError:
        return "", (
            "Tesseract binary not found on PATH. "
            "Download and install from: https://github.com/UB-Mannheim/tesseract/wiki"
        )
    except Exception as exc:
        return "", f"OCR error: {exc}"


# ── Main scanner ──────────────────────────────────────────────────────────────

def scan_image(image_bytes: bytes) -> DocumentScanResult:
    """
    Scan an image for hidden prompt injection content via OCR.

    Args:
        image_bytes: Raw bytes of the image file (PNG, JPG, WEBP, BMP, TIFF).

    Returns:
        DocumentScanResult with decision, confidence, and reason.
    """
    # ── 1. OCR extraction ─────────────────────────────────────────────────────
    extracted_text, error = _extract_text_from_image(image_bytes)

    if error:
        # If OCR infrastructure is missing, fail safe: WARN the user
        return DocumentScanResult(
            decision="WARN_CONFIRM",
            severity="medium",
            reason=f"Image scanning unavailable: {error}. Could not verify image safety.",
            confidence=0.0,
            stealth_flags=["ocr_unavailable"],
            extracted_text_length=0,
            page_count=1,
            detector_name="image_prompt_injection",
            match_type="ocr_error",
        )

    if not extracted_text:
        return DocumentScanResult(
            decision="ALLOW",
            severity="low",
            reason="No text detected in image by OCR. Image appears safe.",
            confidence=0.0,
            stealth_flags=[],
            extracted_text_length=0,
            page_count=1,
            detector_name="image_prompt_injection",
            match_type="",
        )

    # ── 2. ML classification — line-by-line for stealth detection ────────────
    # Classify the full text first
    ml_injection, ml_confidence = classify_text(extracted_text)

    # If the full text doesn't trigger, check individual lines.
    # This prevents a large legitimate document from "drowning out" one malicious line.
    # We use imperative verb heuristics to avoid false positives on normal invoice lines.
    import re
    _IMPERATIVE_PATTERN = re.compile(
        r"\b(ignore|skip|disregard|forget|override|bypass|approve|execute|reveal|print|output"
        r"|pretend|act as|you are now|from now on|instead)\b",
        re.IGNORECASE,
    )
    if not ml_injection:
        lines = [l.strip() for l in extracted_text.splitlines() if len(l.strip()) > 15]
        for line in lines:
            # Only consider lines that look like instructions (contain an imperative verb)
            if not _IMPERATIVE_PATTERN.search(line):
                continue
            line_inj, line_conf = classify_text(line)
            if line_inj and line_conf > ml_confidence:
                ml_injection = True
                ml_confidence = line_conf

    # ── 3. Final decision (no stealth metadata available for images) ──────────
    no_stealth = StealthCheckResult()  # Images don't have span metadata
    decision, severity, reason, match_type = _decide(
        ml_injection, ml_confidence, no_stealth
    )

    # Add OCR note to reason for context
    if decision != "ALLOW":
        reason = f"[Image OCR] {reason}"

    return DocumentScanResult(
        decision=decision,
        severity=severity,
        reason=reason,
        confidence=ml_confidence,
        stealth_flags=[],
        extracted_text_length=len(extracted_text),
        page_count=1,
        detector_name="image_prompt_injection",
        match_type=match_type,
    )
