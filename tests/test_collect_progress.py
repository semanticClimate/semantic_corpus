"""Tests for collect title scroller."""

from __future__ import annotations

from io import StringIO

from semantic_corpus.corpus_review.collect_progress import (
    CollectTitleScroller,
    clean_title,
    title_from_paper,
)


def test_clean_title_strips_markup_and_truncates():
    assert clean_title("<i>AMOC</i> and climate") == "AMOC and climate"
    assert clean_title("") == "(no title)"
    long = "word " * 40
    out = clean_title(long, max_len=20)
    assert len(out) <= 20
    assert out.endswith("…")


def test_title_from_paper():
    assert title_from_paper({"title": "Hello <b>World</b>"}) == "Hello World"


def test_scroller_non_tty_prints_lines():
    buf = StringIO()
    # Force non-live path
    scroller = CollectTitleScroller(limit=3, height=5, stream=buf)
    scroller._live = False
    scroller.start(query="AMOC", repository="europe_pmc")
    scroller.add(title="First paper about AMOC", paper_id="PMC1", status="ok")
    scroller.add(title="Second paper", paper_id="PMC2", status="skip")
    scroller.add(title="Failed preprint", paper_id="X", status="fail")
    scroller.finish()
    text = buf.getvalue()
    assert "europe_pmc" in text
    assert "First paper about AMOC" in text
    assert "Second paper" in text
    assert "Failed preprint" not in text  # fails are status-only
    assert scroller.kept == 2
    assert scroller.n_fail == 1
    assert "kept=2/3" in text


def test_scroller_fails_do_not_count_toward_limit():
    buf = StringIO()
    scroller = CollectTitleScroller(limit=2, height=5, stream=buf)
    scroller._live = False
    scroller.start(query="AMOC", repository="europe_pmc")
    for i in range(5):
        scroller.add(title=f"fail {i}", status="fail")
    scroller.add(title="kept one", paper_id="PMC1", status="ok")
    assert scroller.kept == 1
    assert scroller.n_fail == 5
    assert "[  1/2]" in buf.getvalue()
