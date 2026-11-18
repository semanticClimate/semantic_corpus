"""Tests for cluster-review Step 1: load existing BAGIT corpus."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_corpus.cluster_review.step0 import create_corpus_from_query
from semantic_corpus.cluster_review.step1 import (
    find_metadata_dir,
    list_demo_corpora,
    load_bagit_corpus,
    resolve_bagit_root,
)
from semantic_corpus.core.exceptions import CorpusError


def _fake_search_download(
    *,
    query_string: str,
    repository: str,
    limit: int,
    output_dir: Path,
    formats,
    start_date: str = None,
    end_date: str = None,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for i in range(limit):
        pmcid = f"PMC8{i:06d}"
        Path(output_dir, f"{pmcid}.xml").write_text(
            f"<article><title>Step1 paper {i}</title></article>",
            encoding="utf-8",
        )
        results.append(
            {
                "pmcid": pmcid,
                "title": f"Step1 paper {i}",
                "abstract": f"Abstract {i}",
                "authors": [{"fullName": "Tester"}],
                "publication_date": "2024-06-01",
            }
        )
    return results, len(results)


@pytest.fixture
def mini_bagit(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        "semantic_corpus.cluster_review.step0.run_repository_search",
        _fake_search_download,
    )
    corpus_dir = Path(temp_dir, "corpora", "step1_mini")
    create_corpus_from_query(
        query_string="test",
        query_name="step1_mini",
        query_dir=Path(temp_dir, "queries", "step1_mini"),
        limit=2,
        formats=["xml"],
        corpus_dir=corpus_dir,
        create_bagit=True,
    )
    return corpus_dir


class TestResolveBagit:
    def test_missing_path(self, temp_dir: Path) -> None:
        with pytest.raises(CorpusError, match="not found"):
            resolve_bagit_root(Path(temp_dir, "nope"))

    def test_requires_bagit_txt(self, temp_dir: Path) -> None:
        empty = Path(temp_dir, "empty")
        empty.mkdir()
        with pytest.raises(CorpusError, match="Not a BAGIT"):
            resolve_bagit_root(empty)

    def test_resolves_root(self, mini_bagit: Path) -> None:
        root = resolve_bagit_root(mini_bagit)
        assert Path(root, "bagit.txt").is_file()
        meta = find_metadata_dir(root)
        assert meta.is_dir()
        assert list(meta.glob("*_metadata.json"))


class TestLoadBagitCorpus:
    def test_load_mini_bag(self, mini_bagit: Path) -> None:
        summary = load_bagit_corpus(
            mini_bagit,
            query_name="step1_mini",
            query_string="test",
        )
        assert summary["step"] == 1
        assert summary["paper_count"] == 2
        assert len(summary["papers"]) == 2
        assert summary["papers"][0]["title"]
        assert Path(summary["bag_root"], "bagit.txt").is_file()
        assert summary["row_count"] >= 2

    def test_prefers_existing_review_table(self, mini_bagit: Path) -> None:
        review_dir = Path(mini_bagit, "review")
        review_dir.mkdir(parents=True, exist_ok=True)
        custom = [
            {
                "paper_id": "custom_only",
                "title": "Custom row",
                "review_status": "include",
                "has_xml": True,
                "has_pdf": False,
                "score": 9,
            }
        ]
        review_path = Path(review_dir, "review_table.json")
        review_path.write_text(json.dumps(custom), encoding="utf-8")

        summary = load_bagit_corpus(mini_bagit, write_review_if_missing=False)
        assert summary["review_source"].endswith("review_table.json")
        assert summary["rows"][0]["paper_id"] == "custom_only"

    def test_list_demo_corpora_filters_missing(self, temp_dir: Path) -> None:
        found = list_demo_corpora(project_root=temp_dir)
        assert found == {}
