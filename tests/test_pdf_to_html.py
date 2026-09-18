"""Tests for PDF to HTML (and XML) conversion using Docling."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.transformation.pdf_to_html import (
    convert_corpus_pdf_to_html,
    convert_pdf_to_html,
    convert_pdf_to_xml,
    ensure_corpus_formats,
    get_docling_converter,
)


def _make_mock_converter():
    """Create a mock Docling converter returning dummy HTML and DocTags."""
    mock_conv = MagicMock()
    mock_doc = MagicMock()
    mock_doc.export_to_html.return_value = (
        "<!DOCTYPE html><html><head><title>Mock Paper</title></head>"
        "<body><h1>Mock Paper</h1><p>Sample content.</p></body></html>"
    )
    mock_doc.export_to_doctags.return_value = (
        "<doctag><section_header_level_1>Mock Paper</section_header_level_1>"
        "<text>Sample content.</text></doctag>"
    )
    mock_res = MagicMock()
    mock_res.document = mock_doc
    mock_conv.convert.return_value = mock_res
    return mock_conv


def test_convert_pdf_to_html_missing_file(tmp_path):
    missing_pdf = tmp_path / "missing.pdf"
    output_html = tmp_path / "out.html"
    with pytest.raises(CorpusError, match="PDF file not found"):
        convert_pdf_to_html(missing_pdf, output_html)


def test_convert_pdf_to_html_with_mock(tmp_path):
    fake_pdf = tmp_path / "paper1.pdf"
    fake_pdf.write_bytes(b"%PDF-dummy")
    output_html = tmp_path / "paper1.html"

    mock_conv = _make_mock_converter()
    res = convert_pdf_to_html(
        fake_pdf,
        output_html,
        docling_converter=mock_conv,
        metadata={"title": "Custom Title"},
    )

    assert res == output_html
    assert output_html.exists()
    content = output_html.read_text(encoding="utf-8")
    assert "<title>Custom Title</title>" in content
    assert "<p>Sample content.</p>" in content


def test_convert_pdf_to_html_and_xml_with_mock(tmp_path):
    fake_pdf = tmp_path / "paper2.pdf"
    fake_pdf.write_bytes(b"%PDF-dummy")
    output_html = tmp_path / "paper2.html"
    output_xml = tmp_path / "paper2.xml"

    mock_conv = _make_mock_converter()
    convert_pdf_to_html(
        fake_pdf,
        output_html,
        xml_path=output_xml,
        generate_xml=True,
        docling_converter=mock_conv,
    )

    assert output_html.exists()
    assert output_xml.exists()
    xml_content = output_xml.read_text(encoding="utf-8")
    assert "<?xml" in xml_content
    assert "<doctag>" in xml_content


def test_convert_pdf_to_xml_with_mock(tmp_path):
    fake_pdf = tmp_path / "paper3.pdf"
    fake_pdf.write_bytes(b"%PDF-dummy")
    output_xml = tmp_path / "paper3.xml"

    mock_conv = _make_mock_converter()
    res = convert_pdf_to_xml(
        fake_pdf,
        output_xml,
        docling_converter=mock_conv,
    )

    assert res == output_xml
    assert output_xml.exists()
    xml_content = output_xml.read_text(encoding="utf-8")
    assert "<doctag>" in xml_content


def test_convert_corpus_pdf_to_html(tmp_path):
    corpus_dir = tmp_path / "test_corpus"
    pdf_dir = corpus_dir / "data" / "documents" / "pdf"
    pdf_dir.mkdir(parents=True)

    pdf1 = pdf_dir / "paper_a.pdf"
    pdf1.write_bytes(b"%PDF-dummy1")
    pdf2 = pdf_dir / "paper_b.pdf"
    pdf2.write_bytes(b"%PDF-dummy2")

    mock_conv = _make_mock_converter()
    with patch(
        "semantic_corpus.transformation.pdf_to_html.get_docling_converter",
        return_value=mock_conv,
    ):
        written = convert_corpus_pdf_to_html(corpus_dir, generate_xml=True)

    assert "paper_a" in written
    assert "paper_b" in written
    assert written["paper_a"].exists()
    assert (corpus_dir / "data" / "documents" / "xml" / "paper_a.xml").exists()
    assert (corpus_dir / "data" / "documents" / "xml" / "paper_b.xml").exists()


def test_ensure_corpus_formats_both_origins(tmp_path):
    """Test ensure_corpus_formats harmonizes both XML-origin and PDF-origin papers."""
    corpus_dir = tmp_path / "hybrid_corpus"
    docs_dir = corpus_dir / "data" / "documents"
    xml_dir = docs_dir / "xml"
    pdf_dir = docs_dir / "pdf"
    xml_dir.mkdir(parents=True)
    pdf_dir.mkdir(parents=True)

    # Paper 1 originated from XML (e.g. Europe PMC)
    sample_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<article article-type="research-article">\n'
        '  <front>\n'
        '    <article-meta>\n'
        '      <title-group><article-title>XML Paper</article-title></title-group>\n'
        '      <abstract><p>Abstract text.</p></abstract>\n'
        '    </article-meta>\n'
        '  </front>\n'
        '  <body><p>Body paragraph.</p></body>\n'
        '</article>'
    )
    (xml_dir / "xml_paper.xml").write_text(sample_xml, encoding="utf-8")

    # Paper 2 originated from PDF (e.g. arXiv / SciELO)
    (pdf_dir / "pdf_paper.pdf").write_bytes(b"%PDF-dummy")

    mock_conv = _make_mock_converter()
    with patch(
        "semantic_corpus.transformation.pdf_to_html.get_docling_converter",
        return_value=mock_conv,
    ):
        summary = ensure_corpus_formats(corpus_dir)

    assert "xml_paper" in summary["converted_xml_to_html"]
    assert "pdf_paper" in summary["converted_pdf_to_html"]
    assert "pdf_paper" in summary["converted_pdf_to_xml"]

    # Both papers now have both HTML and XML available
    html_dir = docs_dir / "html"
    assert (html_dir / "xml_paper.html").exists()
    assert (xml_dir / "xml_paper.xml").exists()
    assert (html_dir / "pdf_paper.html").exists()
    assert (xml_dir / "pdf_paper.xml").exists()
    assert summary["papers"]["xml_paper"]["has_both_html_and_xml"] is True
    assert summary["papers"]["pdf_paper"]["has_both_html_and_xml"] is True
