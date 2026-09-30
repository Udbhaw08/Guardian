"""
detectors/document_utils/stealth_rules.py
-------------------------------------------
Rule-based hidden text detection for PDFs.

Analyses PyMuPDF span metadata to detect text that is visually concealed
from human readers but still extractable by AI models:

  - Tiny font size (< 4pt) — text too small to read
  - White-on-white / same color as background — invisible text
  - Near-zero opacity — transparent text
  - Off-page coordinates — text placed outside visible page bounds
  - Hidden OCR layers (e.g., searchable PDF layers over scanned pages)

ARCHITECTURAL CONSTRAINT: No MCP, SSE, or transport types here.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── Thresholds ────────────────────────────────────────────────────────────────

# Text smaller than this is considered invisible to normal readers
TINY_FONT_THRESHOLD_PT: float = 4.0

# Minimum opacity to be considered visible
MIN_VISIBLE_OPACITY: float = 0.05

# PyMuPDF represents RGB colors as integers packed from 0x000000 to 0xFFFFFFFF
# White = 0xFFFFFF (16777215). Near-white threshold: each channel > 240
_WHITE_CHANNEL_THRESHOLD = 240


@dataclass
class StealthCheckResult:
    """Result of stealth rule checks on a single text span."""
    flags: list[str] = field(default_factory=list)
    severity: str = "low"   # "low" | "medium" | "high" | "critical"
    is_suspicious: bool = False

    def _recalculate(self) -> None:
        """Recalculate severity and is_suspicious from current flags."""
        self.is_suspicious = len(self.flags) > 0
        if "white_on_white" in self.flags or "hidden_layer" in self.flags:
            self.severity = "critical"
        elif self.flags:
            self.severity = "high"
        else:
            self.severity = "low"


def _is_near_white(color_int: int | None) -> bool:
    """
    Return True if the color integer represents a near-white color.

    PyMuPDF encodes RGB as a packed integer:
        R = (color >> 16) & 0xFF
        G = (color >> 8)  & 0xFF
        B =  color        & 0xFF
    """
    if color_int is None:
        return False
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    return r > _WHITE_CHANNEL_THRESHOLD and g > _WHITE_CHANNEL_THRESHOLD and b > _WHITE_CHANNEL_THRESHOLD


def check_stealth_flags(
    span: dict,
    page_rect: tuple[float, float, float, float] | None = None,
) -> StealthCheckResult:
    """
    Analyse a single PyMuPDF text span for hidden text indicators.

    Args:
        span:      A dict from page.get_text("rawdict")["blocks"][...]["lines"][...]["spans"].
                   Expected keys: "size", "color", "opacity", "origin", "bbox", "flags".
        page_rect: Optional (x0, y0, x1, y1) bounds of the page.
                   Used to detect off-page text. If None, off-page check is skipped.

    Returns:
        StealthCheckResult with flags and severity.
    """
    result = StealthCheckResult()

    font_size = span.get("size", 12.0)
    color = span.get("color")
    opacity = span.get("alpha", 1.0)   # PyMuPDF uses "alpha" key
    origin = span.get("origin", (0, 0))
    bbox = span.get("bbox")

    # ── Rule 1: Tiny font ────────────────────────────────────────────────────
    if font_size < TINY_FONT_THRESHOLD_PT:
        result.flags.append("tiny_font")

    # ── Rule 2: White / near-white text (invisible on white background) ───────
    if _is_near_white(color):
        result.flags.append("white_on_white")

    # ── Rule 3: Near-zero opacity (transparent text) ─────────────────────────
    if opacity is not None and opacity < MIN_VISIBLE_OPACITY:
        result.flags.append("near_zero_opacity")

    # ── Rule 4: Off-page coordinates ─────────────────────────────────────────
    if page_rect and bbox:
        px0, py0, px1, py1 = page_rect
        bx0, by0, bx1, by1 = bbox
        if bx1 < px0 or bx0 > px1 or by1 < py0 or by0 > py1:
            result.flags.append("off_page")

    result._recalculate()
    return result


def aggregate_stealth_results(results: list[StealthCheckResult]) -> StealthCheckResult:
    """
    Merge multiple span-level StealthCheckResults into one document-level result.

    The highest severity among all individual results wins.
    All unique flags are collected.
    """
    severity_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    merged = StealthCheckResult()

    for r in results:
        if not r.is_suspicious:
            continue
        merged.is_suspicious = True
        for flag in r.flags:
            if flag not in merged.flags:
                merged.flags.append(flag)
        if severity_rank.get(r.severity, 0) > severity_rank.get(merged.severity, 0):
            merged.severity = r.severity

    return merged
