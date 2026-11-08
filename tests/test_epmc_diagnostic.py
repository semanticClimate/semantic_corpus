"""Tests for novice Europe PMC preflight diagnostic."""

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


def test_explain_500_for_novices():
    guide = explain_status(500)
    assert guide.code_label == "500"
    assert "Europe PMC" in guide.meaning
    assert "later" in guide.advice.lower()
    assert guide.severity == "fail"
    blurb = short_status_blurb(500)
    assert "500" in blurb
    assert "later" in blurb.lower()


def test_explain_ok_and_429():
    assert explain_status(200).severity == "ok"
    assert "rate limited" in explain_status(429).meaning.lower()


def test_diagnostic_ok(monkeypatch):
    class SearchOK:
        status_code = 200
        text = '{"hitCount":1}'

        def json(self):
            return {"hitCount": 1, "resultList": {"result": []}}

    class XmlOK:
        status_code = 200
        content = b'<?xml version="1.0"?><article/>'

    def fake_get(url, *args, **kwargs):
        if "fullTextXML" in str(url):
            return XmlOK()
        return SearchOK()

    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_diagnostic.requests.get", fake_get
    )
    diag = run_epmc_diagnostic()
    assert diag.ok
    text = format_epmc_diagnostic(diag)
    assert "Europe PMC check" in text
    assert "Ready" in text
    assert "OK" in text


def test_diagnostic_reports_500_and_aborts(monkeypatch):
    class SearchOK:
        status_code = 200
        text = '{"hitCount":1}'

        def json(self):
            return {"hitCount": 1}

    class Xml500:
        status_code = 500
        content = b'{"status":500,"error":"Internal Server Error"}'
        text = content.decode()

    def fake_get(url, *args, **kwargs):
        if "fullTextXML" in str(url):
            return Xml500()
        return SearchOK()

    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_diagnostic.requests.get", fake_get
    )
    buf = StringIO()
    with pytest.raises(EpmcUnavailable, match="500"):
        epmc_preflight(stream=buf, abort=True)
    out = buf.getvalue()
    assert "500" in out
    assert "Come back later" in out
    assert "Stopped before collect" in out
    assert "Traceback" not in out
    assert "hitCount" not in out


def test_diagnostic_timeout(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.Timeout("slow")

    monkeypatch.setattr(
        "semantic_corpus.repositories.epmc_diagnostic.requests.get", boom
    )
    diag = run_epmc_diagnostic()
    assert not diag.ok
    assert any(p.guide.code_label == "timeout" for p in diag.probes)
