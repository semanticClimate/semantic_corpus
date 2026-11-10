"""Tests for pipeline doit reporter status labels."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from semantic_corpus.pipeline.doit_reporter import (
    PipelineReporter,
    status_label_from_disk,
    status_label_from_streams,
    status_label_for_result,
)


def test_status_label_from_streams():
    assert status_label_from_streams(["json", "xml-http:500"]) == "xml=500"
    assert status_label_from_streams(["json", "xml"]) == "ok"
    assert status_label_from_streams(["no_pmcid"]) == "no_pmcid"
    assert status_label_from_streams(["json", "pdf-http:403"]) == "pdf=403"


def test_status_label_from_disk(tmp_path: Path, monkeypatch):
    pkt = tmp_path / "data" / "packets"
    pkt.mkdir(parents=True)
    (pkt / "PMC1.json").write_text(
        '{"pmcid":"PMC1","_collect_xml":"no_pmcid"}', encoding="utf-8"
    )
    (pkt / "PMC2.json").write_text(
        '{"pmcid":"PMC2","_collect_xml_http":500}', encoding="utf-8"
    )
    (pkt / "PMC3.json").write_text('{"pmcid":"PMC3"}', encoding="utf-8")
    (pkt / "PMC3.xml").write_text(
        '<?xml version="1.0"?><article><body><p>x</p></body></article>',
        encoding="utf-8",
    )
    assert status_label_from_disk(tmp_path, "PMC1") == "no_pmcid"
    assert status_label_from_disk(tmp_path, "PMC2") == "xml=500"
    assert status_label_from_disk(tmp_path, "PMC3") == "ok"


def test_status_label_for_result_prefers_return_dict(tmp_path: Path):
    assert (
        status_label_for_result(
            {"status_label": "xml=403", "streams": ["xml-http:500"]},
            tmp_path,
            "PMC9",
        )
        == "xml=403"
    )


def test_reporter_prints_legend_and_paper_suffix(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("PIPELINE_WORKDIR", str(tmp_path))
    pkt = tmp_path / "data" / "packets"
    pkt.mkdir(parents=True)
    (pkt / "PMC1.json").write_text(
        '{"pmcid":"PMC1","_collect_xml":"no_pmcid"}', encoding="utf-8"
    )

    buf = StringIO()
    rep = PipelineReporter(buf, {})

    class Task:
        def __init__(self, name, result=None):
            self.name = name
            self.result = result
            self.values = result or {}
            self.actions = [object()]
            self.executed = True

        def title(self):
            return self.name

    rep.initialize({}, [])
    rep.skip_uptodate(Task("paper:PMC1"))
    rep.add_success(
        Task("paper:PMC2", {"streams": ["xml-http:500"], "status_label": "xml=500"})
    )
    out = buf.getvalue()
    assert "marks:" in out
    assert "-- paper:PMC1  [no_pmcid]" in out
    assert ".  paper:PMC2  [xml=500]" in out
