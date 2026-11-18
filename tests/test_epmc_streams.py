"""Tests for independent JSON / XML / PDF streams + Docling XML fallback."""

from __future__ import annotations

import json
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


def test_xml_500_is_logged_stream_stays_active(tmp_path: Path, monkeypatch):
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
    # Stream stays on so later papers are still probed; error is logged.
    assert board.is_active(STREAM_XML)
    assert board.is_active(STREAM_PDF)
    assert len(board.errors_for(STREAM_XML)) == 1
    assert board.errors_for(STREAM_XML)[0].status_code == 500
    assert board.errors_for(STREAM_XML)[0].paper_id == "PMC1"
    pkt = tmp_path / "data" / "packets"
    assert (pkt / "PMC1.pdf").is_file()
    assert (pkt / "PMC1.json").is_file()
    assert (pkt / "PMC1.pdf.xml").is_file()
    assert not (pkt / "PMC1.xml").is_file()
    assert "xml-from-pdf" in (result.get("streams") or [])


def test_xml_500s_accumulate_across_papers(tmp_path: Path, monkeypatch):
    board = EpmcStreamBoard()

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
    repo = EuropePMCRepository()
    for pmc in ("PMC1", "PMC2", "PMC3"):
        repo.download_paper(
            pmc,
            tmp_path,
            formats=["xml"],
            paper={"pmcid": pmc, "abstract": "a"},
            streams=board,
            use_docling_xml=False,
        )
    assert board.is_active(STREAM_XML)
    assert len(board.errors_for(STREAM_XML)) == 3
    assert board.format_status_counts() == "500(3)"
    assert board.format_status_counts(STREAM_XML) == "500(3)"
    panel = board.format_panel(final=True)
    assert "Finished" in panel
    assert "500(3)" in panel
    assert "Continuing" not in panel
    report = board.write_error_report(tmp_path / "pipeline" / "epmc_http_errors.json")
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["error_counts"]["xml"] == 3
    assert data["error_counts_by_status"] == {"500": 3}
    assert {e["paper_id"] for e in data["http_errors"]} == {"PMC1", "PMC2", "PMC3"}


def test_format_status_counts_mixed():
    board = EpmcStreamBoard()
    board.record_http_error(STREAM_XML, status_code=500, paper_id="a")
    board.record_http_error(STREAM_XML, status_code=500, paper_id="b")
    board.record_http_error(STREAM_XML, status_code=403, paper_id="c")
    board.record_http_error(STREAM_PDF, status_code=403, paper_id="d")
    board.record_http_error(STREAM_PDF, status_code=404, paper_id="e")
    assert board.format_status_counts() == "403(2), 404(1), 500(2)"
    assert board.format_status_counts(STREAM_XML) == "403(1), 500(2)"
    assert "HTTP 403(1), 500(2)" in board.format_panel(final=True)


def test_skip_existing_xml_and_pdf_no_network(tmp_path: Path, monkeypatch):
    pkt = tmp_path / "data" / "packets"
    pkt.mkdir(parents=True)
    (pkt / "PMC9.xml").write_bytes(_GOOD_XML)
    (pkt / "PMC9.pdf").write_bytes(_GOOD_PDF)
    (pkt / "PMC9.json").write_text(
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
