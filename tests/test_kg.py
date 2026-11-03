"""Tests for post-cluster knowledge graph build + HTML."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from semantic_corpus.cluster_review.kg import (
    build_kg,
    collapse_encyclopedia_synonyms,
    detect_islands,
    links_from_clusters,
    load_paper_titles,
    select_kg_terms,
)


def _mini_clusters(root: Path, *, with_phrases_terms: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "clusters").mkdir(exist_ok=True)
    doc = {
        "step": 3,
        "clusters": [
            {
                "cluster_id": 1,
                "paper_ids": ["p1", "p2"],
                "terms": [
                    {"phrase": "amoc", "display": "AMOC", "weight": 4.0},
                    {
                        "phrase": "north atlantic",
                        "display": "North Atlantic",
                        "weight": 3.0,
                    },
                    {
                        "phrase": "rare phrase",
                        "display": "Rare Phrase",
                        "weight": 9.0,
                    },
                ],
            }
        ],
    }
    (root / "clusters" / "clusters.json").write_text(
        json.dumps(doc), encoding="utf-8"
    )
    if with_phrases_terms:
        phrases = root / "phrases"
        phrases.mkdir(exist_ok=True)
        with (phrases / "phrases_terms.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "phrase",
                    "display",
                    "n_papers",
                    "best_score",
                    "score_channel",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "phrase": "amoc",
                    "display": "AMOC",
                    "n_papers": 2,
                    "best_score": 4.0,
                    "score_channel": "uppercase",
                }
            )
            writer.writerow(
                {
                    "phrase": "north atlantic",
                    "display": "North Atlantic",
                    "n_papers": 2,
                    "best_score": 3.0,
                    "score_channel": "uppercase",
                }
            )
            writer.writerow(
                {
                    "phrase": "rare phrase",
                    "display": "Rare Phrase",
                    "n_papers": 1,
                    "best_score": 9.0,
                    "score_channel": "uppercase",
                }
            )
    return root


def test_links_from_clusters_bipartite(tmp_path: Path):
    workdir = _mini_clusters(tmp_path / "corp")
    nodes, edges = links_from_clusters(workdir)
    kinds = {n["kind"] for n in nodes}
    assert kinds == {"paper", "term"}
    assert any(e["link_source"] == "clusters" for e in edges)
    assert any(e["from"].startswith("paper:") or e["to"].startswith("paper:") for e in edges)


def test_paper_node_tooltip_uses_title(tmp_path: Path):
    workdir = _mini_clusters(tmp_path / "corp")
    meta = workdir / "data" / "metadata"
    meta.mkdir(parents=True)
    (meta / "p1_metadata.json").write_text(
        json.dumps({"title": "Deep Atlantic overturning study"}),
        encoding="utf-8",
    )
    assert load_paper_titles(workdir)["p1"] == "Deep Atlantic overturning study"
    nodes, _edges = links_from_clusters(workdir)
    paper = next(n for n in nodes if n["id"] == "paper:p1")
    assert "Deep Atlantic overturning study" in paper["title"]
    assert paper.get("paper_title") == "Deep Atlantic overturning study"


def test_select_kg_terms_filters_by_paper_count_and_cap(tmp_path: Path):
    workdir = _mini_clusters(tmp_path / "corp", with_phrases_terms=True)
    allowed, n_map, source = select_kg_terms(
        workdir, min_paper_count=2, max_terms=10
    )
    assert source == "phrases_terms"
    assert allowed == {"amoc", "north atlantic"}
    assert n_map["amoc"] == 2

    allowed_cap, _, _ = select_kg_terms(
        workdir, min_paper_count=1, max_terms=1
    )
    assert allowed_cap == {"amoc"}  # highest n_papers then score


def test_build_kg_writes_html(tmp_path: Path):
    workdir = _mini_clusters(tmp_path / "corp", with_phrases_terms=True)
    summary = build_kg(
        workdir,
        kg_links=("clusters",),
        max_island=20,
        min_paper_count=2,
        max_terms=10,
        write_html=True,
        open_browser=False,
    )
    assert Path(summary["graph_path"]).is_file()
    assert Path(summary["html_path"]).is_file()
    assert Path(summary["islands_path"]).is_file()
    html = Path(summary["html_path"]).read_text(encoding="utf-8")
    assert "vis-network" in html
    assert summary["counts"]["papers"] == 2
    assert summary["counts"]["terms"] == 2
    assert summary["params"]["min_paper_count"] == 2
    assert summary["params"]["max_terms"] == 10
    assert "rare phrase" not in {
        n["id"]
        for n in json.loads(Path(summary["graph_path"]).read_text())["nodes"]
    }


def test_collapse_encyclopedia_synonyms_merges_blues_drops_lone_greens():
    nodes = {
        "term:amoc": {
            "id": "term:amoc",
            "kind": "term",
            "group": "Term",
            "label": "AMOC",
            "phrase": "amoc",
            "n_papers": 7,
            "value": 12.0,
            "title": "AMOC",
        },
        "term:atlantic meridional overturning circulation": {
            "id": "term:atlantic meridional overturning circulation",
            "kind": "term",
            "group": "Term",
            "label": "Atlantic Meridional Overturning Circulation",
            "phrase": "atlantic meridional overturning circulation",
            "n_papers": 6,
            "value": 11.0,
            "title": "AMOC long name",
        },
        "term:monsoon": {
            "id": "term:monsoon",
            "kind": "term",
            "group": "Term",
            "label": "Monsoon",
            "phrase": "monsoon",
            "n_papers": 3,
            "value": 10.0,
            "title": "Monsoon",
        },
        "wiki:Q1": {
            "id": "wiki:Q1",
            "kind": "encyclopedia",
            "group": "Encyclopedia",
            "label": "Atlantic meridional overturning circulation",
            "wiki_title": "Atlantic meridional overturning circulation",
            "wikidata_id": "Q1",
        },
        "wiki:Q2": {
            "id": "wiki:Q2",
            "kind": "encyclopedia",
            "group": "Encyclopedia",
            "label": "Monsoon",
            "wiki_title": "Monsoon",
            "wikidata_id": "Q2",
        },
        "paper:p1": {
            "id": "paper:p1",
            "kind": "paper",
            "group": "Paper",
            "label": "p1",
        },
    }
    edges = {
        "e1": {
            "id": "e1",
            "from": "term:amoc",
            "to": "wiki:Q1",
            "source": "term:amoc",
            "target": "wiki:Q1",
            "weight": 2.0,
            "link_source": "wikipedia",
        },
        "e2": {
            "id": "e2",
            "from": "term:atlantic meridional overturning circulation",
            "to": "wiki:Q1",
            "source": "term:atlantic meridional overturning circulation",
            "target": "wiki:Q1",
            "weight": 2.0,
            "link_source": "wikipedia",
        },
        "e3": {
            "id": "e3",
            "from": "term:monsoon",
            "to": "wiki:Q2",
            "source": "term:monsoon",
            "target": "wiki:Q2",
            "weight": 2.0,
            "link_source": "wikipedia",
        },
        "e4": {
            "id": "e4",
            "from": "paper:p1",
            "to": "term:amoc",
            "source": "paper:p1",
            "target": "term:amoc",
            "weight": 1.0,
            "link_source": "clusters",
        },
        "e5": {
            "id": "e5",
            "from": "paper:p1",
            "to": "term:atlantic meridional overturning circulation",
            "source": "paper:p1",
            "target": "term:atlantic meridional overturning circulation",
            "weight": 1.0,
            "link_source": "clusters",
        },
    }
    out_nodes, out_edges, stats = collapse_encyclopedia_synonyms(nodes, edges)
    assert stats["synonym_groups"] == 1
    assert stats["terms_merged"] == 1
    assert "term:atlantic meridional overturning circulation" not in out_nodes
    assert "term:amoc" in out_nodes
    # wiki label preferred on merged blue
    assert out_nodes["term:amoc"]["label"] == (
        "Atlantic meridional overturning circulation"
    )
    # lone green (Monsoon) and synonym-bridge green both dropped
    assert "wiki:Q1" not in out_nodes
    assert "wiki:Q2" not in out_nodes
    assert stats["encyclopedia_dropped"] == 2
    # paper edges remapped onto canonical term
    endpoints = {(e["from"], e["to"]) for e in out_edges.values()}
    assert ("paper:p1", "term:amoc") in endpoints or (
        "term:amoc",
        "paper:p1",
    ) in endpoints


def test_detect_islands_small_components():
    nodes = [
        {"id": "a", "kind": "term"},
        {"id": "b", "kind": "term"},
        {"id": "c", "kind": "paper"},
    ]
    edges = [{"from": "a", "to": "b", "id": "1"}]
    islands = detect_islands(nodes, edges, max_island=5)
    sizes = sorted(i["size"] for i in islands)
    assert 1 in sizes  # singleton c
    assert 2 in sizes  # a-b
