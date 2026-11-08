"""Tests for collect title scroller."""

from __future__ import annotations

from collections import Counter
from io import StringIO

import requests

from semantic_corpus.corpus_review.collect_progress import (
    CollectTitleScroller,
    clean_title,
    fail_reason_label,
    format_fail_breakdown,
    title_from_paper,
)
from semantic_corpus.core.exceptions import RepositoryError


def test_clean_title_strips_markup_and_truncates():
    assert clean_title("<i>AMOC</i> and climate") == "AMOC and climate"
    assert clean_title("") == "(no title)"
    long = "word " * 40
    out = clean_title(long, max_len=20)
    assert len(out) <= 20
    assert out.endswith("…")


def test_title_from_paper():
    assert title_from_paper({"title": "Hello <b>World</b>"}) == "Hello World"


def test_fail_reason_label_http_and_messages():
    assert fail_reason_label("No files downloaded for PMC1 (HTTP 403)") == "403"
    assert fail_reason_label("404 Client Error: Not Found for url: x") == "404"
    assert fail_reason_label("No PMCID found for 123") == "no_pmcid"
    assert fail_reason_label("No files downloaded for PMC1") == "no_files"
    assert fail_reason_label("403") == "403"
    assert fail_reason_label(RepositoryError("No files downloaded (HTTP 503)")) == "503"
    assert (
        fail_reason_label(
            RepositoryError("No files downloaded for PMC1", status_code=500)
        )
        == "500"
    )

    resp = requests.models.Response()
    resp.status_code = 403
    err = requests.HTTPError("403 Client Error", response=resp)
    assert fail_reason_label(err) == "403"


def test_format_fail_breakdown_orders_http_first():
    counts = Counter({"404": 8, "403": 5, "no_files": 1})
    assert format_fail_breakdown(counts) == "403: 5 404: 8 no_files: 1"


def test_scroller_non_tty_prints_lines():
    buf = StringIO()
    # Force non-live path
    scroller = CollectTitleScroller(limit=3, height=5, stream=buf)
    scroller._live = False
    scroller.start(query="AMOC", repository="europe_pmc")
    scroller.add(title="First paper about AMOC", paper_id="PMC1", status="ok")
    scroller.add(title="Second paper", paper_id="PMC2", status="skip")
    scroller.add(title="Failed preprint", paper_id="X", status="fail", reason="403")
    scroller.finish()
    text = buf.getvalue()
    assert "europe_pmc" in text
    assert "First paper about AMOC" in text
    assert "Second paper" in text
    assert "Failed preprint" not in text  # fails are status-only
    assert scroller.kept == 2
    assert scroller.n_fail == 1
    assert "kept=2/3" in text
    assert "403: 1" in text


def test_scroller_fails_do_not_count_toward_limit():
    buf = StringIO()
    scroller = CollectTitleScroller(limit=2, height=5, stream=buf)
    scroller._live = False
    scroller.start(query="AMOC", repository="europe_pmc")
    for i in range(5):
        scroller.add(title=f"fail {i}", status="fail", reason="404")
    scroller.add(title="kept one", paper_id="PMC1", status="ok")
    assert scroller.kept == 1
    assert scroller.n_fail == 5
    assert scroller.fail_reasons["404"] == 5
    assert "[  1/2]" in buf.getvalue()


def test_scroller_status_line_shows_breakdown():
    buf = StringIO()
    scroller = CollectTitleScroller(limit=10, height=5, stream=buf)
    scroller._live = True
    scroller.start(query="AMOC", repository="europe_pmc")
    for _ in range(5):
        scroller.add(title="x", status="fail", reason="403")
    for _ in range(8):
        scroller.add(title="y", status="fail", reason="404")
    status = scroller._status_line()
    assert "failed=13" in status
    assert "403: 5" in status
    assert "404: 8" in status
