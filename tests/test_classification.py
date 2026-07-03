"""Tests for pure-Python paper classification (unsupervised + encyclopedia)."""

import csv
from pathlib import Path

import pytest

from semantic_corpus.classification.annotate import (
    annotate_rows_with_clusters,
    annotate_rows_with_encyclopedia,
    documents_from_review_rows,
    documents_from_search_results,
)
from semantic_corpus.classification.encyclopedia_labels import (
    classify_by_vocabularies,
    load_encyclopedia_categories,
    load_wordlist_terms,
)
from semantic_corpus.classification.unsupervised import (
    cluster_documents,
    top_terms_per_cluster,
)
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.review_schema import make_review_row


AIR_DOCS = {
    "p1": "Air quality index and PM2.5 pollution in Delhi India respiratory health",
    "p2": "Ambient air pollution particulate matter exposure mortality in India cities",
    "p3": "Climate change global warming greenhouse gas emissions mitigation adaptation",
    "p4": "Carbon dioxide emissions net zero decarbonisation climate policy warming",
}


class TestUnsupervised:
    def test_cluster_documents_separates_topics(self) -> None:
        assignments = cluster_documents(AIR_DOCS, n_clusters=2, seed=1)
        assert len(assignments) == 4
        assert assignments["p1"] == assignments["p2"], "air docs should cluster together"
        assert assignments["p3"] == assignments["p4"], "climate docs should cluster together"
        assert assignments["p1"] != assignments["p3"], "topics should be separate clusters"

    def test_cluster_is_deterministic(self) -> None:
        first = cluster_documents(AIR_DOCS, n_clusters=2, seed=7)
        second = cluster_documents(AIR_DOCS, n_clusters=2, seed=7)
        assert first == second, "clustering should be deterministic for a fixed seed"

    def test_top_terms_per_cluster(self) -> None:
        assignments = cluster_documents(AIR_DOCS, n_clusters=2, seed=1)
        terms = top_terms_per_cluster(AIR_DOCS, assignments, top_n=3)
        assert all(len(v) <= 3 for v in terms.values())
        assert terms, "should return terms for each cluster"

    def test_empty_documents(self) -> None:
        assert cluster_documents({}, n_clusters=3) == {}


class TestEncyclopediaVocabularies:
    _CATEGORIES = {
        "climate": ["climate change", "global warming", "greenhouse gas", "emissions"],
        "air_quality": ["air quality index", "pm2.5", "particulate matter", "aqi"],
    }

    def test_classify_by_vocabularies_assigns_best_category(self) -> None:
        results = classify_by_vocabularies(AIR_DOCS, self._CATEGORIES)
        assert results["p1"]["category"] == "air_quality"
        assert results["p3"]["category"] == "climate"
        assert 0.0 < results["p3"]["score"] <= 1.0, "score is a cosine similarity"
        assert results["p3"]["matched_terms"], "should record matched terms"

    def test_unmatched_document_is_unclassified(self) -> None:
        docs = {"x": "completely unrelated text about cooking recipes"}
        results = classify_by_vocabularies(docs, self._CATEGORIES)
        assert results["x"]["category"] == ""
        assert results["x"]["score"] == 0

    def test_load_wordlist_terms(self, tmp_path: Path) -> None:
        csv_path = Path(tmp_path, "raw_wordlist_curated.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["term", "count", "manual_delete"])
            writer.writerow(["climate change", "61", "No"])
            writer.writerow(["deleted term", "5", "Yes"])
            writer.writerow(["low count", "1", "No"])
        terms = load_wordlist_terms(csv_path, min_count=2)
        assert "climate change" in terms
        assert "deleted term" not in terms, "manual_delete=Yes should be excluded"
        assert "low count" not in terms, "below min_count should be excluded"

    def test_load_encyclopedia_categories(self, tmp_path: Path) -> None:
        run_dir = Path(tmp_path, "temp", "ipcc", "phase1_run")
        run_dir.mkdir(parents=True)
        csv_path = Path(run_dir, "raw_wordlist_curated.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["term", "count", "manual_delete"])
            writer.writerow(["climate change", "61", "No"])
            writer.writerow(["adaptation", "48", "No"])
        categories = load_encyclopedia_categories(tmp_path, min_count=2)
        assert "ipcc" in categories, f"expected clean category name, got {list(categories)}"
        assert "climate change" in categories["ipcc"]

    def test_missing_encyclopedia_dir_raises(self, tmp_path: Path) -> None:
        with pytest.raises(CorpusError):
            load_encyclopedia_categories(Path(tmp_path, "does_not_exist"))


class TestAnnotate:
    def _rows(self):
        rows = []
        for doc_id, text in AIR_DOCS.items():
            title, _, abstract = text.partition(" ")
            rows.append(
                make_review_row(
                    paper_id=doc_id,
                    metadata={"title": title, "abstract": text},
                    score=1,
                    location_terms=[],
                    pollutant_terms=[],
                    health_terms=[],
                    has_xml=False,
                    has_pdf=False,
                )
            )
        return rows

    def test_annotate_rows_with_clusters(self) -> None:
        rows = self._rows()
        cluster_terms = annotate_rows_with_clusters(
            rows, documents=AIR_DOCS, n_clusters=2
        )
        assert cluster_terms
        assert all(row["cluster_id"] != "" for row in rows)

    def test_annotate_rows_with_encyclopedia(self) -> None:
        rows = self._rows()
        categories = {
            "climate": ["climate change", "global warming", "emissions"],
            "air_quality": ["air quality", "pm2.5", "particulate matter"],
        }
        annotate_rows_with_encyclopedia(rows, categories, documents=AIR_DOCS)
        by_id = {row["paper_id"]: row for row in rows}
        assert by_id["p3"]["encyclopedia_category"] == "climate"

    def test_documents_from_review_rows(self) -> None:
        rows = self._rows()
        docs = documents_from_review_rows(rows)
        assert set(docs.keys()) == set(AIR_DOCS.keys())

    def test_documents_from_search_results(self, tmp_path: Path) -> None:
        import json

        results = [
            {"pmcid": "PMC1", "pmid": "1", "title": "A", "abstract": "air quality"},
            {"pmcid": "", "pmid": "2", "title": "B", "abstract": "climate change"},
        ]
        path = Path(tmp_path, "search_results.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(results, handle)
        docs = documents_from_search_results(path)
        assert "europe_pmc_PMC1" in docs
        assert "europe_pmc_2" in docs


class TestReviewRowClassificationColumns:
    def test_pdf_path_and_classification_defaults(self) -> None:
        row = make_review_row(
            paper_id="p1",
            metadata={"title": "T", "abstract": "A"},
            score=1,
            location_terms=[],
            pollutant_terms=[],
            health_terms=[],
            has_xml=False,
            has_pdf=True,
            pdf_path="/tmp/p1.pdf",
        )
        assert row["pdf_path"] == "/tmp/p1.pdf"
        assert row["cluster_id"] == ""
        assert row["encyclopedia_category"] == ""
