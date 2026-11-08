"""Tests for cluster-review Step 0: query → download → optional BAGIT."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from semantic_corpus.cluster_review.step0 import create_corpus_from_query
from semantic_corpus.core.exceptions import CorpusError


def _fake_search_download(
    *,
    query_string: str,
    repository: str,
    limit: int,
    output_dir: Path,
    formats: List[str],
    start_date: str = None,
    end_date: str = None,
    on_paper=None,
    **_kwargs,
):
    """Write tiny XML files and return synthetic search hits."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    for i in range(limit):
        pmcid = f"PMC9{i:06d}"
        xml_path = Path(output_dir, f"{pmcid}.xml")
        xml_path.write_text(
            f"<article><title>Paper {i} about {query_string}</title></article>",
            encoding="utf-8",
        )
        paper = {
            "pmcid": pmcid,
            "pmid": str(1000 + i),
            "title": f"Paper {i} about climate",
            "abstract": f"Abstract {i} for testing Step 0.",
            "doi": f"10.1000/test.{i}",
            "authors": [{"fullName": f"Author {i}"}],
            "publication_date": "2024-01-01",
            "journal": "Test Journal",
        }
        results.append(paper)
        if on_paper is not None:
            on_paper(paper, "ok")
    return results, len(results)


class TestCreateCorpusFromQueryValidation:
    def test_rejects_empty_query(self, temp_dir: Path) -> None:
        with pytest.raises(CorpusError, match="query_string"):
            create_corpus_from_query(
                query_string="  ",
                query_name="demo",
                query_dir=Path(temp_dir, "q"),
            )

    def test_rejects_unknown_repository(self, temp_dir: Path) -> None:
        with pytest.raises(CorpusError, match="Unknown repository"):
            create_corpus_from_query(
                query_string="climate",
                query_name="demo",
                query_dir=Path(temp_dir, "q"),
                repositories="not_a_real_repo",
                create_bagit=False,
            )

    def test_bagit_requires_corpus_dir(self, temp_dir: Path) -> None:
        with pytest.raises(CorpusError, match="corpus_dir"):
            create_corpus_from_query(
                query_string="climate",
                query_name="demo",
                query_dir=Path(temp_dir, "q"),
                create_bagit=True,
                corpus_dir=None,
            )


class TestCreateCorpusFromQueryHappyPath:
    def test_query_dir_and_bagit(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "semantic_corpus.cluster_review.step0.run_repository_search",
            _fake_search_download,
        )
        query_dir = Path(temp_dir, "queries", "step0_demo")
        corpus_dir = Path(temp_dir, "corpora", "step0_demo")

        summary = create_corpus_from_query(
            query_string="marine heatwave",
            query_name="step0_demo",
            query_dir=query_dir,
            repositories="europe_pmc",
            limit=3,
            formats=["xml"],
            corpus_dir=corpus_dir,
            create_bagit=True,
        )

        assert summary["step"] == 0
        assert summary["result_count"] == 3
        assert summary["downloaded_count"] == 3
        assert summary["bagit_paper_count"] == 3
        assert Path(summary["search_results_path"]).is_file()
        assert Path(summary["query_dir"], "review", "review_table.json").is_file()
        assert Path(corpus_dir, "bagit.txt").is_file()

        results = json.loads(Path(summary["search_results_path"]).read_text(encoding="utf-8"))
        assert len(results) == 3
        assert results[0]["pmcid"].startswith("PMC")

    def test_skip_bagit(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "semantic_corpus.cluster_review.step0.run_repository_search",
            _fake_search_download,
        )
        query_dir = Path(temp_dir, "queries", "raw_only")
        summary = create_corpus_from_query(
            query_string="ocean",
            query_name="raw_only",
            query_dir=query_dir,
            limit=2,
            create_bagit=False,
        )
        assert summary["create_bagit"] is False
        assert summary["bagit_paper_count"] == 0
        assert summary["corpus_dir"] == ""
        assert Path(query_dir, "search_results.json").is_file()

    def test_multi_repo_fills_limit(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: List[str] = []

        def _tracking_search(**kwargs):
            calls.append(kwargs["repository"])
            output_dir = Path(kwargs["output_dir"])
            output_dir.mkdir(parents=True, exist_ok=True)
            limit = int(kwargs["limit"])
            on_paper = kwargs.get("on_paper")
            # Distinct PMCID namespaces per repo so merges do not collide
            base = 100000 if kwargs["repository"] == "europe_pmc" else 200000
            # First repo only contributes one paper so the second repo is used
            n = 1 if kwargs["repository"] == "europe_pmc" else limit
            results = []
            for i in range(n):
                pmcid = f"PMC{base + i}"
                Path(output_dir, f"{pmcid}.xml").write_text(
                    f"<article><title>{pmcid}</title></article>",
                    encoding="utf-8",
                )
                paper = {
                    "pmcid": pmcid,
                    "title": f"{kwargs['repository']} paper {i}",
                    "abstract": "test",
                    "authors": [],
                }
                results.append(paper)
                if on_paper is not None:
                    on_paper(paper, "ok")
            return results, len(results)

        monkeypatch.setattr(
            "semantic_corpus.cluster_review.step0.run_repository_search",
            _tracking_search,
        )
        summary = create_corpus_from_query(
            query_string="climate",
            query_name="multi",
            query_dir=Path(temp_dir, "q_multi"),
            repositories=["europe_pmc", "openalex"],
            limit=3,
            create_bagit=False,
        )
        assert calls == ["europe_pmc", "openalex"]
        assert summary["repositories"] == ["europe_pmc", "openalex"]
        assert summary["result_count"] == 3
        assert len(summary["per_repo"]) == 2
