"""Tests for legacy extractor → sectioner → indexed_text."""

from __future__ import annotations

from pathlib import Path

import pytest

from semantic_corpus.corpus.legacy import legacy_to_indexed_text, list_extractors
from semantic_corpus.corpus.legacy.extractors import (
    PymupdfExtractor,
    get_extractor,
)

RESOURCES = Path(__file__).resolve().parent / "resources" / "input_adapters"
PDF = RESOURCES / "layout_specimen.pdf"
OA_PDF = RESOURCES / "oa_pdf_html_pair" / "ClimateEU_PMC7719169.pdf"
HTML_SPECIMEN = RESOURCES / "layout_specimen.html"


def test_list_extractors_includes_pymupdf() -> None:
    pytest.importorskip("pymupdf")
    names = list_extractors()
    assert "pymupdf" in names


def test_pymupdf_extractor_emits_paragraphs(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    if not PDF.is_file():
        pytest.skip("layout_specimen.pdf missing")
    result = PymupdfExtractor().extract(PDF, outdir=tmp_path)
    assert result.engine == "pymupdf"
    assert "<p>" in result.html
    assert "SPECIMEN_START_PAGE" in result.html
    assert "SPECIMEN_END_PAGE" in result.html
    assert result.meta.get("pages") == 3


def test_legacy_pipeline_pymupdf_mints_ids(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    if not PDF.is_file():
        pytest.skip("layout_specimen.pdf missing")
    indexed = legacy_to_indexed_text(
        PDF,
        extractor="pymupdf",
        paper_id="layout_specimen",
        refine="none",
        outdir=tmp_path,
        write_html=True,
    )
    assert indexed["type"] == "indexed_text"
    assert indexed["extractor"] == "pymupdf"
    assert indexed["blocks"]
    joined = "\n".join(b["text"] for b in indexed["blocks"])
    assert "SPECIMEN_START_PAGE" in joined
    assert "SPECIMEN_VERSO" in joined
    assert "SPECIMEN_END_PAGE" in joined
    assert any(b["id"].startswith("layout_specimen#") for b in indexed["blocks"])
    assert 'data-tb-kind="' in indexed["html"]
    assert (tmp_path / "layout_specimen.indexed.html").is_file()


def test_legacy_pipeline_html_sectioner_only() -> None:
    indexed = legacy_to_indexed_text(
        HTML_SPECIMEN,
        extractor="html",
        paper_id="layout_specimen",
        refine="none",
    )
    assert indexed["extractor"] == "html"
    assert indexed["blocks"]
    assert any("FLOAT_FIGURE_CAP" in b["text"] for b in indexed["blocks"])


def test_get_extractor_auto_returns_something() -> None:
    pytest.importorskip("pymupdf")
    eng = get_extractor("auto")
    assert eng.name in {"docling", "amilib", "pymupdf"}


def test_marker_mineru_stubs_raise() -> None:
    with pytest.raises(NotImplementedError):
        get_extractor("marker").extract(HTML_SPECIMEN)


@pytest.mark.slow
def test_legacy_pipeline_oa_pdf_overlap_smoke(tmp_path: Path) -> None:
    """Optional smoke: ClimateEU PDF → indexed_text contains shared keywords."""
    pytest.importorskip("pymupdf")
    if not OA_PDF.is_file():
        pytest.skip("OA PDF fixture missing")
    indexed = legacy_to_indexed_text(
        OA_PDF,
        extractor="pymupdf",
        paper_id="ClimateEU_PMC7719169",
        refine="none",
        outdir=tmp_path,
    )
    joined = "\n".join(b["text"] for b in indexed["blocks"]).lower()
    assert "climate" in joined
    assert len(indexed["blocks"]) >= 10
