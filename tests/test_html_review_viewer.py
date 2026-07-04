"""Tests for HTML review viewer."""

import json
from pathlib import Path

from semantic_corpus.corpus_review.html_viewer import (
    build_filter_summary,
    render_review_viewer_html,
    write_review_viewer,
)
from semantic_corpus.corpus_review.interactive_review import ReviewSessionConfig


def _sample_rows():
    return [
        {
            "review_status": "review",
            "score": 2,
            "paper_id": "europe_pmc_PMC1",
            "pmcid": "PMC1",
            "pmid": "",
            "doi": "",
            "title": "High score paper",
            "publication_date": "2026-01-01",
            "journal": "",
            "authors": "A Author",
            "has_xml": True,
            "has_pdf": True,
            "query_name": "test",
            "query_string": "test",
            "location_terms": "",
            "pollutant_terms": "aqi",
            "health_terms": "health",
            "abstract_snippet": "Abstract one",
            "review_notes": "",
        },
        {
            "review_status": "review",
            "score": 0,
            "paper_id": "europe_pmc_PMC2",
            "pmcid": "PMC2",
            "pmid": "",
            "doi": "",
            "title": "Low score paper",
            "publication_date": "2026-01-01",
            "journal": "",
            "authors": "",
            "has_xml": False,
            "has_pdf": False,
            "query_name": "test",
            "query_string": "test",
            "location_terms": "",
            "pollutant_terms": "",
            "health_terms": "",
            "abstract_snippet": "Abstract two",
            "review_notes": "",
        },
    ]


class TestHtmlReviewViewer:
    def test_filter_summary_shows_min_score_message(self) -> None:
        rows = _sample_rows()
        config = ReviewSessionConfig(
            review_table_path=Path("review_table.json"),
            min_score=1,
        )
        summary = build_filter_summary(rows, config, queue_indices=[0])
        assert summary["queue_count"] == 1
        assert any("only 1 paper reaches min_score >= 1" in msg for msg in summary["messages"])
        assert "min_score >= 1" in summary["headline"]

    def test_write_review_viewer_html(self, tmp_path: Path) -> None:
        review_dir = tmp_path / "review"
        review_dir.mkdir()
        review_table = review_dir / "review_table.json"
        review_table.write_text(json.dumps(_sample_rows()), encoding="utf-8")

        config = ReviewSessionConfig(review_table_path=review_table)
        output = write_review_viewer(config, review_dir / "review_viewer.html")
        html = output.read_text(encoding="utf-8")
        assert "papers in review table" in html
        assert "Include (Y)" in html
        assert "Min score" not in html
        assert "/api/paper-preview" in html
        assert render_review_viewer_html({"papers": [], "queue_indices": []})

    def test_viewer_payload_does_not_embed_full_text(self, tmp_path: Path) -> None:
        from semantic_corpus.corpus_review.html_viewer import build_viewer_payload
        from semantic_corpus.corpus_review.interactive_review import ReviewSession

        review_dir = tmp_path / "review"
        review_dir.mkdir()
        review_table = review_dir / "review_table.json"
        review_table.write_text(json.dumps(_sample_rows()), encoding="utf-8")
        session = ReviewSession.load(ReviewSessionConfig(review_table_path=review_table))
        payload = build_viewer_payload(session)
        paper = payload["papers"][0]
        assert "abstract" not in paper
        assert "intro" not in paper
