"""Tests for independent JSON / XML / PDF streams + Docling XML fallback."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests

from semantic_corpus.repositories.epmc_streams import (
    STREAM_PDF,
    STREAM_XML,
    EpmcStreamBoard,
    maybe_docling_pdf_to_xml,
)
from semantic_corpus.repositories.europe_pmc import EuropePMCRepository

_ERROR_JSON = b'{"status":500,"error":"Internal Server Error"}'
_GOOD_PDF = b"%PDF-1.4\n" + (b"0" * 80)
_GOOD_XML = b'<?xml version="1.0"?><article><body><p>ok</p></body></article>'


def test_xml_500_disables_xml_stream_only(tmp_path: Path, monkeypatch):
    board = EpmcStreamBoard()
    paper = {"pmcid": "PMC1", "title": "T", "abstract": "Abs"}

    class FakeResponse:
        status_code = 500
        content = _ERROR_JSON

        def raise_for_status(self) -> None:
            err = requests.HTTPError("500 Server Error")
            err.response = self
            raise err

    monkeypatch.setattr(
        "semantic_corpus.repositories.europe_pmc.requests.get",
        lambda *a, **k: FakeResponse(),
    )
    monkeypatch.setattr(
        EuropePMCRepository,
        "_download_pdf",
        lambda self, *a, **k: _GOOD_PDF,
    )
    def _fake_docling(pdf, xml, **k):
        Path(xml).parent.mkdir(parents=True, exist_ok=True)
        Path(xml).write_bytes(_GOOD_XML)
        return Path(xml)

    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_streams.maybe_docling_pdf_to_xml",
        _fake_docling,
    )

    repo = EuropePMCRepository()
    result = repo.download_paper(
        "PMC1",
        tmp_path,
        formats=["xml", "pdf"],
        paper=paper,
        streams=board,
        use_docling_xml=True,
    )
    assert result["success"] is True
    assert not board.is_active(STREAM_XML)
    assert board.is_active(STREAM_PDF)
    assert (tmp_path / "PMC1.pdf").is_file()
    assert (tmp_path / "PMC1.json").is_file()
    # Docling synthesized XML after XML stream died → ``{id}.pdf.xml``
    assert (tmp_path / "PMC1.pdf.xml").is_file()
    assert not (tmp_path / "PMC1.xml").is_file()
    assert "xml-from-pdf" in (result.get("streams") or [])


def test_skip_existing_xml_and_pdf_no_network(tmp_path: Path, monkeypatch):
    (tmp_path / "PMC9.xml").write_bytes(_GOOD_XML)
    (tmp_path / "PMC9.pdf").write_bytes(_GOOD_PDF)
    (tmp_path / "PMC9.json").write_text(
        '{"pmcid":"PMC9","abstract":"x"}', encoding="utf-8"
    )

    def _boom(*a, **k):
        raise AssertionError("network should not be called when files exist")

    monkeypatch.setattr(
        "semantic_corpus.repositories.europe_pmc.requests.get", _boom
    )
    monkeypatch.setattr(EuropePMCRepository, "_download_pdf", _boom)

    board = EpmcStreamBoard()
    repo = EuropePMCRepository()
    result = repo.download_paper(
        "PMC9",
        tmp_path,
        formats=["xml", "pdf"],
        paper={"pmcid": "PMC9", "title": "T", "abstract": "A"},
        streams=board,
    )
    assert result["success"] is True
    assert result.get("skipped") is True
    assert "skip-xml" in (result.get("streams") or [])
    assert "skip-pdf" in (result.get("streams") or [])


def test_maybe_docling_pdf_to_xml(tmp_path: Path, monkeypatch):
    pdf = tmp_path / "a.pdf"
    xml = tmp_path / "a.xml"
    pdf.write_bytes(_GOOD_PDF)

    def fake_convert(pdf_path, xml_path, **kwargs):
        Path(xml_path).write_bytes(_GOOD_XML)
        return Path(xml_path)

    monkeypatch.setattr(
        "semantic_corpus.transformation.pdf_to_html.convert_pdf_to_xml",
        fake_convert,
    )
    out = maybe_docling_pdf_to_xml(pdf, xml)
    assert out == xml
    assert xml.read_bytes() == _GOOD_XML
