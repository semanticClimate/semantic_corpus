"""Tests for editable HTML review table export."""

import json
from pathlib import Path

from semantic_corpus.corpus_review.review_table import export_review_tables


def _sample_row(**overrides):
    row = {
        "review_status": "review",
        "score": 0,
        "paper_id": "europe_pmc_PMC1",
        "pmcid": "PMC1",
        "pmid": "",
        "doi": "",
        "title": "Climate anxiety paper",
        "publication_date": "2026-01-01",
        "journal": "",
        "authors": "A Author",
        "has_xml": True,
        "has_pdf": True,
        "query_name": "test",
        "query_string": "test",
        "location_terms": "",
        "pollutant_terms": "",
        "health_terms": "",
        "abstract_snippet": "Sample abstract text.",
        "review_notes": "",
    }
    row.update(overrides)
    return row


class TestHtmlReviewTableExport:
    def test_export_includes_editable_html_and_css(self, tmp_path: Path) -> None:
        paths = export_review_tables([_sample_row()], tmp_path)
        html = paths["html"].read_text(encoding="utf-8")
        css = paths["css"].read_text(encoding="utf-8")

        assert "review-status" in html
        assert "Climate anxiety paper" in html
        assert "btn-read" in html
        assert "paper-reader" in html
        assert "paper-embed" in html
        assert "format-btn" in html
        assert "row-reading" in html
        assert "connection-banner" in html
        assert "checkServer" in html
        assert "SERVE_COMMAND" in html
        assert "review_table.css" in html
        assert ".status-include" in css

    def test_css_not_overwritten_if_user_edited(self, tmp_path: Path) -> None:
        export_review_tables([_sample_row()], tmp_path)
        css_path = tmp_path / "review_table.css"
        css_path.write_text("/* user theme */ body { background: pink; }", encoding="utf-8")
        export_review_tables([_sample_row(review_status="include")], tmp_path)
        assert "pink" in css_path.read_text(encoding="utf-8")

    def test_save_payload_shape_matches_json_columns(self, tmp_path: Path) -> None:
        paths = export_review_tables([_sample_row()], tmp_path)
        rows = json.loads(paths["json"].read_text(encoding="utf-8"))
        assert rows[0]["review_status"] == "review"
        assert rows[0]["title"] == "Climate anxiety paper"
