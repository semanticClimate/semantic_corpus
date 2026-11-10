"""Tests for novice Europe PMC per-stream preflight."""

from __future__ import annotations

from io import StringIO

import pytest
import requests

from semantic_corpus.repositories.epmc_diagnostic import (
    EpmcUnavailable,
    epmc_preflight,
    explain_status,
    format_epmc_diagnostic,
    run_epmc_diagnostic,
    short_status_blurb,
)
from semantic_corpus.repositories.epmc_streams import (
    STREAM_JSON,
    STREAM_PDF,
    STREAM_XML,
)


def test_explain_500_for_novices():
    guide = explain_status(500)
    assert guide.code_label == "500"
    assert "Europe PMC" in guide.meaning
    assert guide.severity == "fail"
    blurb = short_status_blurb(500)
    assert "500" in blurb


def test_diagnostic_all_ok(monkeypatch):
    class SearchOK:
        status_code = 200

        def json(self):
            return {"hitCount": 1}

    def fake_get(url, *args, **kwargs):
        if "fullTextXML" in str(url):
            class XmlOK:
                status_code = 200
                content = b'<?xml version="1.0"?><article/>'

            return XmlOK()
        return SearchOK()

    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_diagnostic.requests.get", fake_get
    )
    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_diagnostic.EuropePMCRepository._download_pdf",
        lambda self, *a, **k: b"%PDF-1.4\n" + (b"0" * 80),
    )
    diag = run_epmc_diagnostic()
    assert diag.ok
    assert diag.all_streams_ok
    text = format_epmc_diagnostic(diag)
    assert "all streams active" in text.lower() or "Ready" in text


def test_xml_500_preflight_keeps_xml_active_and_logs(monkeypatch):
    class SearchOK:
        status_code = 200

        def json(self):
            return {"hitCount": 1}

    class Xml500:
        status_code = 500
        content = b'{"status":500,"error":"Internal Server Error"}'

    def fake_get(url, *args, **kwargs):
        if "fullTextXML" in str(url):
            return Xml500()
        return SearchOK()

    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_diagnostic.requests.get", fake_get
    )
    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_diagnostic.EuropePMCRepository._download_pdf",
        lambda self, *a, **k: b"%PDF-1.4\n" + (b"0" * 80),
    )
    buf = StringIO()
    diag, board = epmc_preflight(stream=buf, abort=True)
    assert diag.ok  # JSON still up
    assert board.is_active(STREAM_JSON)
    assert board.is_active(STREAM_XML)  # stay on — probe every paper
    assert board.is_active(STREAM_PDF)
    assert len(board.errors_for(STREAM_XML)) >= 1
    out = buf.getvalue()
    assert "XML full text" in out
    assert "active" in out
    # Not an alarming "probe 500 — server error" line when stream stays on
    assert "probe 500" not in out
    assert "Stopped — JSON" not in out
    assert "sample check" in out.lower() or "Ready" in out


def test_json_down_aborts(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.Timeout("slow")

    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_diagnostic.requests.get", boom
    )
    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_diagnostic.EuropePMCRepository._download_pdf",
        lambda self, *a, **k: None,
    )
    buf = StringIO()
    with pytest.raises(EpmcUnavailable, match="JSON/search"):
        epmc_preflight(stream=buf, abort=True)


def test_diagnostic_timeout_json(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.Timeout("slow")

    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_diagnostic.requests.get", boom
    )
    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_diagnostic.EuropePMCRepository._download_pdf",
        lambda self, *a, **k: None,
    )
    diag = run_epmc_diagnostic()
    assert not diag.ok
    assert not diag.board.is_active(STREAM_JSON)
