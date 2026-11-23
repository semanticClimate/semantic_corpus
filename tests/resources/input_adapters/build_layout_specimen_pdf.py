#!/usr/bin/env python3
"""Build layout_specimen.pdf (multi-page text-layer) with PyMuPDF.

Default (committed fixture): compact ASCII + Latin diacritics via core fonts
where possible; Greek/Devanagari markers appear as ASCII placeholders plus
separate Unicode fixtures (HTML/TXT/hOCR).

Unicode build (CI/local with Arial Unicode)::

  python tests/resources/input_adapters/build_layout_specimen_pdf.py --unicode

Tests may also build a unicode PDF into a temp path.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional, Tuple

import pymupdf

OUT = Path(__file__).resolve().parent / "layout_specimen.pdf"
_UNICODE_FONTS = [
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
]


def pick_unicode_font() -> Optional[Path]:
    for path in _UNICODE_FONTS:
        if path.is_file():
            return path
    return None


def _write_page(
    page: pymupdf.Page,
    lines: List[Tuple[float, str, float]],
    *,
    fontname: str,
) -> None:
    for y, text, size in lines:
        page.insert_text((72, y), text, fontsize=size, fontname=fontname)


def build(out: Path = OUT, *, unicode_font: bool = False) -> Path:
    """Write a 3-page specimen PDF (start/verso/end, headers/footers, floats)."""
    doc = pymupdf.open()
    w, h = 612, 792
    font_path = pick_unicode_font() if unicode_font else None
    fontname = "helv"

    def new_page() -> pymupdf.Page:
        nonlocal fontname
        page = doc.new_page(width=w, height=h)
        if font_path is not None:
            fontname = "uni"
            page.insert_font(fontname=fontname, fontfile=str(font_path))
        return page

    if font_path is not None:
        greek = "Greek: αβγ and ΔΩθ in running prose."
        deva = "Devanagari: नमस्ते for climate readers."
        diac = "Diacritics: café, naïve, Zürich, São Paulo."
    else:
        # Compact fixture: full Unicode covered by HTML/TXT/hOCR; PDF keeps structure.
        greek = "Greek: alpha-beta-gamma and ALPHA markers (see HTML specimen for αβγ)."
        deva = "Devanagari: namaste marker (see HTML specimen for real नमस्ते)."
        diac = "Diacritics: cafe, naive, Zurich, Sao Paulo (HTML has café/Zürich/São)."

    p1 = new_page()
    _write_page(
        p1,
        [
            (36, "RUNNING_TITLE_CLIMATE - HEADER_PAGE_1", 9),
            (72, "Layout specimen", 18),
            (110, "SPECIMEN_START_PAGE on recto. Marker SPECIMEN_RECTO.", 11),
            (140, diac, 11),
            (170, greek, 11),
            (200, deva, 11),
            (240, "FONT_BOLD example", 11),
            (260, "FONT_ITALIC example", 11),
            (285, "FONT_LARGE example", 16),
            (430, "FLOAT_FIGURE_CAP Wave height schematic.", 10),
            (760, "FOOTER_PAGE_1", 9),
        ],
        fontname=fontname,
    )
    p1.draw_rect(pymupdf.Rect(72, 320, 300, 420), color=(0.5, 0.5, 0.5))

    p2 = new_page()
    _write_page(
        p2,
        [
            (36, "RUNNING_TITLE_CLIMATE - HEADER_PAGE_2", 9),
            (110, "SPECIMEN_VERSO body continues the discussion of heatwaves.", 11),
            (160, "FLOAT_TEXTBOX Sidebar note on marine heatwaves.", 9),
            (260, "FLOAT_TABLE_CAP Example SST anomalies.", 10),
            (280, "Region    dT", 10),
            (295, "Pacific   +1.2", 10),
            (760, "FOOTER_PAGE_2", 9),
        ],
        fontname=fontname,
    )
    p2.draw_rect(pymupdf.Rect(350, 140, 540, 220), color=(0.6, 0.6, 0.6))

    p3 = new_page()
    _write_page(
        p3,
        [
            (36, "RUNNING_TITLE_CLIMATE - HEADER_PAGE_3", 9),
            (110, "Closing remarks. SPECIMEN_END_PAGE on final recto.", 11),
            (760, "FOOTER_PAGE_3", 9),
        ],
        fontname=fontname,
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out, garbage=4, deflate=True)
    doc.close()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--unicode",
        action="store_true",
        help="Embed Arial Unicode when available (large file; for local checks).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUT,
        help="Output PDF path",
    )
    args = parser.parse_args()
    path = build(args.output, unicode_font=args.unicode)
    print(f"Wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
