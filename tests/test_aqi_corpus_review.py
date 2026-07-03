"""Tests for AQI India corpus review workflow."""

import json
import pytest
from pathlib import Path

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.constants import (
    REVIEW_STATUS_INCLUDE,
    REVIEW_STATUS_REVIEW,
)
from semantic_corpus.corpus_review.query_run import (
    build_query_run_record,
    load_pilot_config,
    save_query_run_record,
    summarize_query_run,
)
from semantic_corpus.corpus_review.relevance_scorer import score_paper_relevance
from semantic_corpus.corpus_review.review_schema import (
    filter_rows_by_status,
    make_review_row,
    validate_review_row,
)
from semantic_corpus.corpus_review.review_table import (
    build_review_rows_from_corpus,
    build_review_rows_from_pygetpapers,
    export_review_tables,
)
from semantic_corpus.export.chatbot_export import (
    build_citation_label,
    export_corpus_for_chatbot,
)
from semantic_corpus.ingestion.pygetpapers_ingester import ingest_pygetpapers_directory


def _wildlife_dir() -> Path:
    repo_root = Path(__file__).resolve().parent.parent
    return Path(
        repo_root, "..", "amilib", "test", "resources", "pygetpapers", "wildlife"
    ).resolve()


@pytest.fixture
def pygetpapers_wildlife_dir() -> Path:
    path = _wildlife_dir()
    if not path.exists():
        pytest.skip(f"Wildlife fixture not found: {path}")
    return path


@pytest.fixture
def pilot_config_path() -> Path:
    path = Path(Path(__file__).resolve().parent.parent, "config", "aqi_india_pilot.yaml")
    assert path.is_file(), f"Pilot config missing: {path}"
    return path


class TestPilotConfig:
    def test_load_aqi_india_pilot_config(self, pilot_config_path: Path) -> None:
        config = load_pilot_config(pilot_config_path)
        assert config["query_name"] == "aqi_india_pilot", (
            f"Expected query_name aqi_india_pilot, got {config.get('query_name')}"
        )
        assert "India" in config["query_string"], (
            "Pilot query_string should mention India"
        )
        assert config["repository"] == "europe_pmc"
        assert config["limit"] == 25
        assert config["formats"] == ["xml"]


class TestRelevanceScorer:
    def test_high_score_for_aqi_india_paper(self) -> None:
        metadata = {
            "title": "Air quality index and PM2.5 in Delhi, India",
            "abstract": "Ambient air pollution exposure and respiratory health in India.",
            "doi": "10.1234/test",
            "journal": "Environmental Health",
            "authors": ["Patel, A."],
        }
        score, matched = score_paper_relevance(metadata, has_xml=True)
        assert score >= 5, f"Expected high relevance score, got {score}"
        assert "india" in matched["location_terms"] or "delhi" in matched["location_terms"]
        assert matched["pollutant_terms"], "Expected pollutant term matches"

    def test_low_score_without_india(self) -> None:
        metadata = {
            "title": "Air quality in Europe",
            "abstract": "PM10 levels in western cities.",
        }
        score, _ = score_paper_relevance(metadata, has_xml=False)
        assert score < 3, f"Expected low score without India, got {score}"


class TestReviewSchema:
    def test_make_and_validate_review_row(self, sample_metadata: dict) -> None:
        row = make_review_row(
            paper_id="europe_pmc_PMC999",
            metadata=sample_metadata,
            score=7,
            location_terms=["india"],
            pollutant_terms=["pm2.5"],
            health_terms=["health"],
            has_xml=True,
            has_pdf=False,
            query_name="aqi_india_pilot",
        )
        validate_review_row(row)
        assert row["review_status"] == REVIEW_STATUS_REVIEW

    def test_invalid_review_status_raises(self, sample_metadata: dict) -> None:
        with pytest.raises(CorpusError) as exc_info:
            make_review_row(
                paper_id="p1",
                metadata=sample_metadata,
                score=1,
                location_terms=[],
                pollutant_terms=[],
                health_terms=[],
                has_xml=False,
                has_pdf=False,
                review_status="invalid",
            )
        assert "review_status" in str(exc_info.value)

    def test_filter_rows_by_status(self) -> None:
        rows = [
            {"review_status": REVIEW_STATUS_INCLUDE, "paper_id": "a"},
            {"review_status": REVIEW_STATUS_REVIEW, "paper_id": "b"},
        ]
        included = filter_rows_by_status(rows, REVIEW_STATUS_INCLUDE)
        assert len(included) == 1, f"Expected 1 included row, got {len(included)}"
        assert included[0]["paper_id"] == "a"


class TestReviewTable:
    def test_build_review_rows_from_pygetpapers_wildlife(
        self, pygetpapers_wildlife_dir: Path
    ) -> None:
        rows = build_review_rows_from_pygetpapers(
            pygetpapers_wildlife_dir,
            query_name="wildlife_fixture",
        )
        assert len(rows) >= 9, (
            f"Expected at least 9 review rows from wildlife, got {len(rows)}"
        )
        assert all("score" in r and "title" in r for r in rows)

    def test_export_review_tables(
        self, pygetpapers_wildlife_dir: Path, temp_dir: Path
    ) -> None:
        rows = build_review_rows_from_pygetpapers(pygetpapers_wildlife_dir)
        paths = export_review_tables(rows, temp_dir, basename="aqi_review")
        assert paths["json"].is_file(), f"JSON review table missing at {paths['json']}"
        assert paths["csv"].is_file(), f"CSV review table missing at {paths['csv']}"
        assert paths["markdown"].is_file(), (
            f"Markdown review table missing at {paths['markdown']}"
        )


class TestQueryRun:
    def test_query_run_record_roundtrip(self, temp_dir: Path) -> None:
        record = build_query_run_record(
            query_name="aqi_india_pilot",
            query_string="AQI AND India",
            repository="europe_pmc",
            limit=25,
            formats=["xml"],
            output_dir=temp_dir,
            result_count=20,
            downloaded_count=8,
        )
        path = save_query_run_record(record, temp_dir)
        assert path.is_file(), f"query_run.json should exist at {path}"
        summary = summarize_query_run(record)
        assert "20 results" in summary


class TestChatbotExport:
    def test_citation_label(self, sample_metadata: dict) -> None:
        label = build_citation_label(sample_metadata)
        assert "Sample Article" in label

    def test_export_corpus_for_chatbot(
        self, temp_dir: Path, pygetpapers_wildlife_dir: Path
    ) -> None:
        corpus = CorpusManager(temp_dir, use_bagit=True)
        corpus.create_structured_directories()
        ingest_pygetpapers_directory(pygetpapers_wildlife_dir, corpus)
        rows = build_review_rows_from_corpus(corpus)
        for row in rows[:3]:
            row["review_status"] = REVIEW_STATUS_INCLUDE

        manifest_path = export_corpus_for_chatbot(
            corpus,
            Path(temp_dir, "chatbot_export"),
            review_rows=rows,
            include_only_status=True,
        )
        assert manifest_path.is_file(), f"Manifest missing at {manifest_path}"
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        assert manifest["paper_count"] == 3, (
            f"Expected 3 included papers in manifest, got {manifest['paper_count']}"
        )
        assert manifest["papers"][0].get("citation_label"), (
            "Each paper should have citation_label"
        )


class TestLivePilotSearch:
    @pytest.mark.live_api
    @pytest.mark.network
    def test_run_pilot_search_aqi_india(self, pilot_config_path: Path) -> None:
        from semantic_corpus.corpus_review.workflow import run_pilot_from_config

        record = run_pilot_from_config(pilot_config_path)
        assert record["result_count"] >= 0, "result_count should be non-negative"
        assert Path(record["output_dir"], "query_run.json").is_file(), (
            "query_run.json should be written after pilot search"
        )
        assert Path(record["search_results_path"]).is_file(), (
            "search_results.json should be written after pilot search"
        )
