"""Tests for input-adapter layout specimen fixtures and sectioner conversions."""

from __future__ import annotations

from pathlib import Path

import pytest

from semantic_corpus.corpus.converters.html_to_semantic import html_file_to_semantic
from semantic_corpus.corpus.converters.raw_to_blocks import raw_file_to_semantic
from semantic_corpus.transformation.xml_to_html import convert_xml_to_html

RESOURCES = Path(__file__).resolve().parent / "resources" / "input_adapters"

REQUIRED_MARKERS = [
    "SPECIMEN_START_PAGE",
    "SPECIMEN_END_PAGE",
    "SPECIMEN_RECTO",
    "SPECIMEN_VERSO",
    "RUNNING_TITLE_CLIMATE",
    "HEADER_PAGE_1",
    "HEADER_PAGE_3",
    "FOOTER_PAGE_1",
    "FOOTER_PAGE_3",
    "FLOAT_FIGURE_CAP",
    "FLOAT_TABLE_CAP",
    "FLOAT_TEXTBOX",
    "FONT_BOLD",
    "FONT_ITALIC",
    "FONT_LARGE",
    "café",
    "αβγ",
    "नमस्ते",
]


def _assert_markers(text: str, *, source: str) -> None:
    missing = [m for m in REQUIRED_MARKERS if m not in text]
    assert not missing, f"{source} missing markers: {missing}"


@pytest.mark.parametrize(
    "filename",
    [
        "layout_specimen.html",
        "layout_specimen.jats.xml",
        "layout_specimen.txt",
        "layout_specimen.md",
        "layout_specimen.hocr.html",
    ],
)
def test_specimen_text_fixtures_contain_markers(filename: str) -> None:
    path = RESOURCES / filename
    assert path.is_file(), path
    text = path.read_text(encoding="utf-8")
    _assert_markers(text, source=filename)


def test_html_specimen_has_recto_verso_and_three_pages() -> None:
    html = (RESOURCES / "layout_specimen.html").read_text(encoding="utf-8")
    assert 'data-page="1"' in html and 'data-side="recto"' in html
    assert 'data-page="2"' in html and 'data-side="verso"' in html
    assert 'data-page="3"' in html
    assert html.count("RUNNING_TITLE_CLIMATE") >= 3


def test_hocr_specimen_has_bboxes_on_pages() -> None:
    hocr = (RESOURCES / "layout_specimen.hocr.html").read_text(encoding="utf-8")
    assert 'class="ocr_page"' in hocr
    assert "bbox 0 0 612 792" in hocr
    assert "ppageno 0" in hocr and "ppageno 2" in hocr
    assert 'title="bbox' in hocr


def test_html_to_semantic_mints_ids_and_keeps_markers(tmp_path: Path) -> None:
    result = html_file_to_semantic(
        RESOURCES / "layout_specimen.html",
        paper_id="layout_specimen",
    )
    assert result["blocks"], "expected text_blocks"
    kinds = {b["kind"] for b in result["blocks"]}
    assert "paragraph" in kinds
    assert "figcaption" in kinds or "tablecaption" in kinds or "heading" in kinds
    ids = [b["id"] for b in result["blocks"]]
    assert len(ids) == len(set(ids)), "block ids must be unique"
    joined = "\n".join(b["text"] for b in result["blocks"])
    for marker in (
        "SPECIMEN_START_PAGE",
        "SPECIMEN_END_PAGE",
        "FLOAT_FIGURE_CAP",
        "café",
        "αβγ",
        "नमस्ते",
    ):
        assert marker in joined
    out = tmp_path / "semantic.html"
    out.write_text(result["html"], encoding="utf-8")
    assert 'data-tb-kind="' in out.read_text(encoding="utf-8")


def test_raw_text_to_semantic_preserves_unicode_markers() -> None:
    result = raw_file_to_semantic(
        RESOURCES / "layout_specimen.txt",
        paper_id="layout_specimen",
    )
    assert len(result["blocks"]) >= 3
    joined = "\n".join(b["text"] for b in result["blocks"])
    _assert_markers(joined, source="raw_to_semantic")


def test_jats_specimen_converts_with_xml_to_html(tmp_path: Path) -> None:
    xml_path = RESOURCES / "layout_specimen.jats.xml"
    html_path = tmp_path / "layout_specimen.html"
    convert_xml_to_html(xml_path, html_path)
    text = html_path.read_text(encoding="utf-8")
    for marker in (
        "SPECIMEN_START_PAGE",
        "SPECIMEN_VERSO",
        "SPECIMEN_END_PAGE",
        "FLOAT_FIGURE_CAP",
        "FLOAT_TABLE_CAP",
        "café",
        "αβγ",
        "नमस्ते",
        "FONT_BOLD",
    ):
        assert marker in text
    # Sectioner on converted HTML
    semantic = html_file_to_semantic(html_path, paper_id="layout_specimen")
    assert any("SPECIMEN_START_PAGE" in b["text"] for b in semantic["blocks"])


def test_pdf_specimen_extracts_markers_and_page_count() -> None:
    pdf_path = RESOURCES / "layout_specimen.pdf"
    if not pdf_path.is_file():
        pytest.skip("layout_specimen.pdf missing; run build_layout_specimen_pdf.py")
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open(pdf_path)
    assert doc.page_count == 3, "start, middle (verso), end pages"
    texts = [page.get_text() for page in doc]
    full = "\n".join(texts)
    for marker in (
        "SPECIMEN_START_PAGE",
        "SPECIMEN_END_PAGE",
        "SPECIMEN_RECTO",
        "SPECIMEN_VERSO",
        "RUNNING_TITLE_CLIMATE",
        "HEADER_PAGE_1",
        "FOOTER_PAGE_3",
        "FLOAT_FIGURE_CAP",
        "FLOAT_TEXTBOX",
        "FLOAT_TABLE_CAP",
        "FONT_BOLD",
        "FONT_ITALIC",
        "FONT_LARGE",
    ):
        assert marker in full, marker
    assert "SPECIMEN_START_PAGE" in texts[0]
    assert "SPECIMEN_VERSO" in texts[1]
    assert "SPECIMEN_END_PAGE" in texts[2]


def test_pdf_unicode_build_when_font_available(tmp_path: Path) -> None:
    """Optional: embed system Unicode font and assert Greek/Devanagari extract."""
    import importlib.util

    pymupdf = pytest.importorskip("pymupdf")
    builder = RESOURCES / "build_layout_specimen_pdf.py"
    spec = importlib.util.spec_from_file_location("build_layout_specimen_pdf", builder)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if mod.pick_unicode_font() is None:
        pytest.skip("No Arial Unicode on this machine")
    out = tmp_path / "layout_specimen_unicode.pdf"
    mod.build(out, unicode_font=True)
    assert out.stat().st_size > 1000
    doc = pymupdf.open(out)
    full = "\n".join(page.get_text() for page in doc)
    assert "αβγ" in full
    assert "नमस्ते" in full
    assert "café" in full
