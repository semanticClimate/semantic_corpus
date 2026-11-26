"""Smoke test for IPCC caption bipartite sample."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

EXAMPLE = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "phrases_kg_ipcc_captions"
)


def _load_build_module():
    path = EXAMPLE / "build_bipartite_kg.py"
    spec = importlib.util.spec_from_file_location("build_bipartite_kg_sample", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sample_data_loads_and_has_edges() -> None:
    mod = _load_build_module()
    data = EXAMPLE / "data"
    docs = mod.load_indexed_texts(sorted(data.glob("*.indexed.json")))
    assert len(docs) == 2
    assert {d["paper_id"] for d in docs} == {
        "ipcc_ar6_wgii_ch02",
        "ipcc_ar6_wgii_ch04",
    }
    terms = mod.load_terms(data / "terms.json")
    assert "adaptation" in terms
    captions = mod.figcaption_blocks(docs)
    assert len(captions) >= 6
    edges = mod.build_bipartite_edges(captions, terms)
    assert edges, "expected some term–caption matches"
    assert any(t == "water-related adaptation" for t, _, _ in edges)
    assert any("ch04" in c for _, c, _ in edges)
    assert any("ch02" in c for _, c, _ in edges)


def test_networkx_graph_builds() -> None:
    pytest.importorskip("networkx")
    mod = _load_build_module()
    data = EXAMPLE / "data"
    docs = mod.load_indexed_texts(sorted(data.glob("*.indexed.json")))
    terms = mod.load_terms(data / "terms.json")
    captions = mod.figcaption_blocks(docs)
    edges = mod.build_bipartite_edges(captions, terms)
    G = mod.build_networkx_graph(captions, terms, edges)
    assert G.number_of_edges() == len(edges)
    assert any(d.get("bipartite") == 0 for _, d in G.nodes(data=True))
    assert any(d.get("bipartite") == 1 for _, d in G.nodes(data=True))
