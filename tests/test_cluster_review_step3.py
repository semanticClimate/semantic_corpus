"""Tests for cluster-review Step 3: bipartite clusters."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_corpus.cluster_review.step0 import create_corpus_from_query
from semantic_corpus.cluster_review.step2 import extract_phrases, save_paper_phrases
from semantic_corpus.cluster_review.step3 import (
    build_bipartite_graph,
    build_clusters,
    load_clusters,
    load_graph_summary,
    load_orphans,
    partition_clusters,
)
from semantic_corpus.core.exceptions import CorpusError


def _fake_search(
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
        pmcid = f"PMC9{i:06d}"
        Path(output_dir, f"{pmcid}.xml").write_text(
            f"<article><title>Paper {i}</title></article>",
            encoding="utf-8",
        )
        results.append(
            {
                "pmcid": pmcid,
                "title": f"Paper {i}",
                "abstract": "Abstract text",
                "authors": [{"fullName": "Tester"}],
                "publication_date": "2024-01-01",
            }
        )
    return results, len(results)


def _write_phrase_caches(corpus_dir: Path, mapping: dict) -> None:
    """mapping: paper_id -> list of (phrase, score)."""
    phrases_dir = Path(corpus_dir, "phrases")
    phrases_dir.mkdir(parents=True, exist_ok=True)
    for paper_id, phrases in mapping.items():
        save_paper_phrases(
            Path(phrases_dir, f"{paper_id}.json"),
            paper_id=paper_id,
            phrases=[{"phrase": p, "score": s} for p, s in phrases],
            text_source="test",
            params={"method": "tfidf", "n": 3, "top": 15},
            elapsed_s=0.01,
        )
    index = {
        "step": 2,
        "paper_count": len(mapping),
        "params": {"method": "tfidf"},
        "paper_ids": list(mapping.keys()),
    }
    Path(phrases_dir, "index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )


@pytest.fixture
def phrase_corpus(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        "semantic_corpus.cluster_review.step0.run_repository_search",
        _fake_search,
    )
    corpus_dir = Path(temp_dir, "corpora", "step3_mini")
    create_corpus_from_query(
        query_string="test",
        query_name="step3_mini",
        query_dir=Path(temp_dir, "queries", "step3_mini"),
        limit=4,
        formats=["xml"],
        corpus_dir=corpus_dir,
        create_bagit=True,
    )
    # Two thematic groups + one orphan-ish paper
    _write_phrase_caches(
        corpus_dir,
        {
            "europe_pmc_PMC9000000": [
                ("indian ocean", 0.9),
                ("monsoon", 0.5),
                ("amoc", 0.4),
            ],
            "europe_pmc_PMC9000001": [
                ("indian ocean", 0.8),
                ("monsoon", 0.6),
                ("rainfall", 0.3),
            ],
            "europe_pmc_PMC9000002": [
                ("sea ice", 0.9),
                ("arctic", 0.7),
                ("amoc", 0.2),
            ],
            "europe_pmc_PMC9000003": [
                ("sea ice", 0.85),
                ("arctic", 0.65),
                ("polar", 0.4),
            ],
        },
    )
    return corpus_dir


class TestBuildClusters:
    def test_requires_phrases(self, temp_dir: Path) -> None:
        empty = Path(temp_dir, "empty_corpus")
        empty.mkdir()
        with pytest.raises(CorpusError, match="phrases"):
            build_clusters(empty)

    def test_builds_clusters_and_files(self, phrase_corpus: Path) -> None:
        summary = build_clusters(
            phrase_corpus, resolution=1.0, min_cluster_papers=2, seed=1
        )
        assert summary["step"] == 3
        assert summary["paper_count"] == 4
        assert summary["cluster_count"] >= 1
        assert Path(summary["clusters_path"]).is_file()
        assert Path(summary["orphans_path"]).is_file()
        assert Path(summary["graph_summary_path"]).is_file()

        loaded = load_clusters(phrase_corpus)
        assert loaded is not None
        assert len(loaded["clusters"]) == summary["cluster_count"]
        for cluster in loaded["clusters"]:
            assert cluster["paper_count"] >= 2
            assert cluster["theme"]
            assert cluster["paper_ids"]
            assert cluster["terms"]

        orphans = load_orphans(phrase_corpus)
        assert orphans is not None
        graph = load_graph_summary(phrase_corpus)
        assert graph is not None
        assert graph["edge_count"] == summary["edge_count"]

    def test_bipartite_graph_structure(self, phrase_corpus: Path) -> None:
        from semantic_corpus.cluster_review.step3 import load_phrase_records

        records = load_phrase_records(phrase_corpus)
        graph = build_bipartite_graph(records, score_higher_is_better=True)
        papers = [n for n, d in graph.nodes(data=True) if d["bipartite"] == "paper"]
        terms = [n for n, d in graph.nodes(data=True) if d["bipartite"] == "term"]
        assert len(papers) == 4
        assert "t:indian ocean" in terms
        assert graph.has_edge("p:europe_pmc_PMC9000000", "t:indian ocean")

    def test_partition_marks_small_communities_as_orphans(self) -> None:
        pytest.importorskip("networkx")
        import networkx as nx

        g = nx.Graph()
        g.add_node("p:a", bipartite="paper", label="a")
        g.add_node("p:b", bipartite="paper", label="b")
        g.add_node("p:c", bipartite="paper", label="c")
        g.add_node("t:x", bipartite="term", label="x")
        g.add_node("t:y", bipartite="term", label="y")
        g.add_edge("p:a", "t:x", weight=1.0)
        g.add_edge("p:b", "t:x", weight=1.0)
        g.add_edge("p:c", "t:y", weight=1.0)
        communities = [{"p:a", "p:b", "t:x"}, {"p:c", "t:y"}]
        clusters, orphans = partition_clusters(g, communities, min_cluster_papers=2)
        assert len(clusters) == 1
        assert clusters[0]["paper_ids"] == ["a", "b"]
        assert "c" in orphans["paper_ids"]
