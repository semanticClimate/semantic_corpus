"""Tests for interactive review selection."""

import json
from pathlib import Path

import pytest

from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.constants import (
    REVIEW_STATUS_EXCLUDE,
    REVIEW_STATUS_INCLUDE,
    REVIEW_STATUS_REVIEW,
)
from semantic_corpus.corpus_review.interactive_review import (
    ReviewSession,
    ReviewSessionConfig,
)
from semantic_corpus.corpus_review.text_preview import (
    build_paper_preview,
    extract_intro_from_xml,
    strip_markup,
)


SAMPLE_JATS = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <body>
    <sec>
      <title>Introduction</title>
      <p>Climate anxiety is increasing among adolescents worldwide.</p>
      <p>This study examines coping strategies in urban populations.</p>
    </sec>
    <sec>
      <title>Methods</title>
      <p>We surveyed 500 participants.</p>
    </sec>
  </body>
</article>
"""


class TestTextPreview:
    def test_strip_markup(self) -> None:
        text = "<h4>Background</h4>Climate change affects mental health."
        assert strip_markup(text) == "Background Climate change affects mental health."

    def test_extract_intro_from_xml(self, tmp_path: Path) -> None:
        xml_path = tmp_path / "PMC123.xml"
        xml_path.write_text(SAMPLE_JATS, encoding="utf-8")
        intro = extract_intro_from_xml(xml_path)
        assert "Climate anxiety is increasing" in intro
        assert "Methods" not in intro

    def test_build_paper_preview_uses_xml_intro(self, tmp_path: Path) -> None:
        xml_path = tmp_path / "PMC123.xml"
        xml_path.write_text(SAMPLE_JATS, encoding="utf-8")
        row = {
            "paper_id": "europe_pmc_PMC123",
            "pmcid": "PMC123",
            "title": "Test paper",
            "abstract_snippet": "Short abstract",
            "location_terms": "india",
            "pollutant_terms": "pm2.5",
            "health_terms": "health",
        }
        preview = build_paper_preview(row, xml_dir=tmp_path)
        assert "Climate anxiety is increasing" in preview["intro"]
        assert "india" in preview["topics"]


class TestReviewSession:
    @pytest.fixture
    def review_dir(self, tmp_path: Path) -> Path:
        review_dir = tmp_path / "review"
        review_dir.mkdir()
        rows = [
            {
                "review_status": REVIEW_STATUS_REVIEW,
                "score": 5,
                "paper_id": "europe_pmc_PMC1",
                "pmcid": "PMC1",
                "pmid": "",
                "doi": "",
                "title": "High score India AQI paper",
                "publication_date": "2026-01-01",
                "journal": "Env Health",
                "authors": "A Author",
                "has_xml": True,
                "has_pdf": False,
                "query_name": "test",
                "query_string": "test",
                "location_terms": "india",
                "pollutant_terms": "aqi",
                "health_terms": "health",
                "abstract_snippet": "Air quality and health in India.",
                "review_notes": "",
            },
            {
                "review_status": REVIEW_STATUS_REVIEW,
                "score": 0,
                "paper_id": "europe_pmc_PMC2",
                "pmcid": "PMC2",
                "pmid": "",
                "doi": "",
                "title": "Low score unrelated paper",
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
                "abstract_snippet": "Unrelated topic.",
                "review_notes": "",
            },
        ]
        with open(review_dir / "review_table.json", "w", encoding="utf-8") as handle:
            json.dump(rows, handle)
        return review_dir

    def test_queue_filters_by_score_and_topic(self, review_dir: Path) -> None:
        session = ReviewSession.load(
            ReviewSessionConfig(
                review_table_path=review_dir / "review_table.json",
                min_score=1,
                topic_filter="aqi",
            )
        )
        assert session.total == 1
        assert session.current_row()["paper_id"] == "europe_pmc_PMC1"

    def test_apply_decision_updates_status_and_saves(
        self, review_dir: Path, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        session = ReviewSession.load(
            ReviewSessionConfig(review_table_path=review_dir / "review_table.json")
        )

        continue_session, message = session.apply_decision("y", notes="Looks relevant")
        assert continue_session is True
        assert REVIEW_STATUS_INCLUDE in message
        assert session.rows[0]["review_status"] == REVIEW_STATUS_INCLUDE
        assert session.rows[0]["review_notes"] == "Looks relevant"
        assert (review_dir / "review_table.json").is_file()

        with open(review_dir / "review_table.json", "r", encoding="utf-8") as handle:
            saved = json.load(handle)
        assert saved[0]["review_status"] == REVIEW_STATUS_INCLUDE

    def test_undo_restores_previous_status(self, review_dir: Path) -> None:
        session = ReviewSession.load(
            ReviewSessionConfig(review_table_path=review_dir / "review_table.json")
        )
        session.apply_decision("n")
        session.apply_decision("u")
        assert session.rows[0]["review_status"] == REVIEW_STATUS_REVIEW

    def test_empty_queue_raises(self, review_dir: Path) -> None:
        session = ReviewSession.load(
            ReviewSessionConfig(
                review_table_path=review_dir / "review_table.json",
                min_score=99,
            )
        )
        assert session.total == 0

    def test_format_current_paper_shows_topics(self, review_dir: Path) -> None:
        session = ReviewSession.load(
            ReviewSessionConfig(review_table_path=review_dir / "review_table.json")
        )
        text = session.format_current_paper()
        assert "topics:" in text
        assert "Decision:" in text
