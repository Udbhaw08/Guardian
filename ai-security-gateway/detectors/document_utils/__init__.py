"""
detectors/document_utils/__init__.py
-------------------------------------
Document scanning utilities package.

Exports:
  - classify_text()         — wraps injection_model.pkl for text classification
  - check_stealth_flags()   — rule-based hidden text analysis for PDFs
  - scan_pdf()              — full PDF scan pipeline
  - scan_image()            — full Image OCR + scan pipeline
"""
from detectors.document_utils.classifier import classify_text
from detectors.document_utils.stealth_rules import check_stealth_flags
from detectors.document_utils.pdf_prompt_injection import scan_pdf
from detectors.document_utils.image_prompt_injection import scan_image

__all__ = ["classify_text", "check_stealth_flags", "scan_pdf", "scan_image"]
