"""Step 3: bipartite paper–phrase clusters (read-only view artifacts).

Loads ``<corpus>/phrases/``, builds a bipartite graph, runs Louvain community
detection, and writes ``<corpus>/clusters/`` (does not modify review tables).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from semantic_corpus.cluster_review.step2 import (
    load_cached_phrases,
    load_phrase_index,
    normalize_phrase,
    phrases_dir_for_corpus,
    prefer_phrase_display,
)
from semantic_corpus.core.exceptions import CorpusError

DEFAULT_RESOLUTION = 1.0
DEFAULT_MIN_CLUSTER_PAPERS = 2
DEFAULT_ALGORITHM = "louvain"
PAPER_PREFIX = "p:"
TERM_PREFIX = "t:"


def clusters_dir_for_corpus(corpus_dir: Path) -> Path:
    return Path(corpus_dir, "clusters")


def _require_networkx():
    try:
        import networkx as nx
    except ImportError as exc:
        import sys

        raise CorpusError(
            "networkx is required for Step 3. Install:\n"
            f"  {sys.executable} -m pip install networkx\n"
            "or: pip install 'semantic_corpus[cluster_review]'\n"
            f"(current python: {sys.executable})"
        ) from exc
    return nx


def load_phrase_records(
    corpus_dir: Path,
    *,
    paper_ids: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """Load per-paper phrase JSON caches (skips index/CSV)."""
    phrases_dir = phrases_dir_for_corpus(corpus_dir)
    if not phrases_dir.is_dir():
        raise CorpusError(
            f"No phrases directory at {phrases_dir}. Run Step 2 first."
        )
    wanted: Optional[Set[str]] = set(paper_ids) if paper_ids is not None else None
    records: List[Dict[str, Any]] = []
    for path in sorted(phrases_dir.glob("*.json")):
        if path.name == "index.json":
            continue
        data = load_cached_phrases(path)
        if data is None:
            continue
        paper_id = str(data.get("paper_id") or path.stem)
        if wanted is not None and paper_id not in wanted:
            continue
        records.append(data)
    if not records:
        raise CorpusError(
            f"No phrase cache JSON files under {phrases_dir}. Run Step 2 first."
        )
    return records


def _edge_weight(score: Any, *, score_higher_is_better: bool) -> float:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return 1.0
    if score_higher_is_better:
        return max(value, 1e-9)
    # YAKE: lower is better → invert for edge strength
    return 1.0 / max(value, 1e-9)


def build_bipartite_graph(
    records: Sequence[Dict[str, Any]],
    *,
    score_higher_is_better: bool = True,
) -> Any:
    """Build an undirected bipartite NetworkX graph (paper ↔ term)."""
    nx = _require_networkx()
    graph = nx.Graph()
    for record in records:
        paper_id = str(record.get("paper_id") or "")
        if not paper_id:
            continue
        paper_node = f"{PAPER_PREFIX}{paper_id}"
        graph.add_node(paper_node, bipartite="paper", label=paper_id)
        for item in record.get("phrases") or []:
            phrase = normalize_phrase(item.get("phrase") or "")
            if not phrase:
                continue
            term_node = f"{TERM_PREFIX}{phrase}"
            display = prefer_phrase_display(
                phrase,
                item.get("display") if isinstance(item.get("display"), str) else None,
            )
            weight = _edge_weight(
                item.get("score"), score_higher_is_better=score_higher_is_better
            )
            if not graph.has_node(term_node):
                graph.add_node(
                    term_node, bipartite="term", label=phrase, display=display
                )
            else:
                graph.nodes[term_node]["display"] = prefer_phrase_display(
                    graph.nodes[term_node].get("display"), display
                )
            if graph.has_edge(paper_node, term_node):
                graph[paper_node][term_node]["weight"] += weight
            else:
                graph.add_edge(paper_node, term_node, weight=weight)
    return graph


def _detect_communities(
    graph: Any,
    *,
    algorithm: str = DEFAULT_ALGORITHM,
    resolution: float = DEFAULT_RESOLUTION,
    seed: int = 42,
) -> List[Set[str]]:
    nx = _require_networkx()
    if graph.number_of_nodes() == 0:
        return []
    algorithm = (algorithm or DEFAULT_ALGORITHM).strip().lower()
    if algorithm == "louvain":
        try:
            communities = nx.community.louvain_communities(
                graph, weight="weight", resolution=resolution, seed=seed
            )
            return [set(c) for c in communities]
        except Exception:
            algorithm = "greedy"
    if algorithm != "greedy":
        raise CorpusError(
            f"Unknown cluster algorithm {algorithm!r}; use 'louvain' or 'greedy'"
        )
    try:
        communities = nx.community.greedy_modularity_communities(
            graph, weight="weight", resolution=resolution
        )
    except TypeError:
        # Older networkx without resolution kwarg
        communities = nx.community.greedy_modularity_communities(
            graph, weight="weight"
        )
    return [set(c) for c in communities]


def _theme_from_terms(
    term_weights: Dict[str, float],
    *,
    displays: Optional[Dict[str, str]] = None,
    top_n: int = 5,
) -> str:
    if not term_weights:
        return "(no terms)"
    ranked = sorted(term_weights.items(), key=lambda kv: (-kv[1], kv[0]))
    labels = displays or {}
    return "; ".join(labels.get(t) or t for t, _ in ranked[:top_n])


def partition_clusters(
    graph: Any,
    communities: Sequence[Set[str]],
    *,
    min_cluster_papers: int = DEFAULT_MIN_CLUSTER_PAPERS,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Split communities into multi-paper clusters vs orphans."""
    clusters: List[Dict[str, Any]] = []
    orphan_papers: List[str] = []
    orphan_terms: List[str] = []
    cluster_id = 0

    # Papers with no edges are orphans even if absent from communities
    all_paper_nodes = {
        n for n, d in graph.nodes(data=True) if d.get("bipartite") == "paper"
    }
    covered_papers: Set[str] = set()

    for community in sorted(
        communities,
        key=lambda c: (
            -sum(1 for n in c if n.startswith(PAPER_PREFIX)),
            -len(c),
        ),
    ):
        paper_ids = sorted(
            graph.nodes[n]["label"]
            for n in community
            if n.startswith(PAPER_PREFIX) and n in graph
        )
        term_labels = sorted(
            graph.nodes[n]["label"]
            for n in community
            if n.startswith(TERM_PREFIX) and n in graph
        )
        covered_papers.update(f"{PAPER_PREFIX}{pid}" for pid in paper_ids)

        if len(paper_ids) < min_cluster_papers:
            orphan_papers.extend(paper_ids)
            # Terms only attached to orphan-sized communities → term orphans
            orphan_terms.extend(term_labels)
            continue

        # Term weights inside cluster: sum of edge weights to cluster papers
        term_weights: Dict[str, float] = {}
        term_displays: Dict[str, str] = {}
        for term in term_labels:
            tnode = f"{TERM_PREFIX}{term}"
            weight = 0.0
            for paper_id in paper_ids:
                pnode = f"{PAPER_PREFIX}{paper_id}"
                if graph.has_edge(pnode, tnode):
                    weight += float(graph[pnode][tnode].get("weight") or 0.0)
            term_weights[term] = weight
            term_displays[term] = prefer_phrase_display(
                term, graph.nodes[tnode].get("display") if tnode in graph else None
            )

        ranked_terms = [
            {
                "phrase": phrase,
                "display": term_displays.get(phrase) or phrase,
                "weight": round(weight, 4),
            }
            for phrase, weight in sorted(
                term_weights.items(), key=lambda kv: (-kv[1], kv[0])
            )
        ]
        cluster_id += 1
        clusters.append(
            {
                "cluster_id": cluster_id,
                "theme": _theme_from_terms(term_weights, displays=term_displays),
                "paper_count": len(paper_ids),
                "term_count": len(term_labels),
                "paper_ids": paper_ids,
                "terms": ranked_terms,
            }
        )

    for pnode in sorted(all_paper_nodes - covered_papers):
        orphan_papers.append(graph.nodes[pnode]["label"])

    # Deduplicate orphans while preserving order
    def _uniq(items: List[str]) -> List[str]:
        seen: Set[str] = set()
        out: List[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    orphans = {
        "paper_ids": _uniq(orphan_papers),
        "terms": _uniq(orphan_terms),
        "paper_count": 0,
        "term_count": 0,
    }
    orphans["paper_count"] = len(orphans["paper_ids"])
    orphans["term_count"] = len(orphans["terms"])
    return clusters, orphans


def build_clusters(
    corpus_dir: Path,
    *,
    algorithm: str = DEFAULT_ALGORITHM,
    resolution: float = DEFAULT_RESOLUTION,
    min_cluster_papers: int = DEFAULT_MIN_CLUSTER_PAPERS,
    paper_ids: Optional[Sequence[str]] = None,
    seed: int = 42,
) -> Dict[str, Any]:
    """Step 3: build bipartite clusters from cached phrases.

    Writes under ``<corpus_dir>/clusters/``:
      - ``clusters.json``
      - ``orphans.json``
      - ``graph_summary.json``
    """
    corpus_dir = Path(corpus_dir)
    if resolution <= 0:
        raise CorpusError("resolution must be > 0")
    if min_cluster_papers < 1:
        raise CorpusError("min_cluster_papers must be >= 1")

    t0 = time.perf_counter()
    index = load_phrase_index(corpus_dir)
    records = load_phrase_records(corpus_dir, paper_ids=paper_ids)

    method = None
    if index:
        method = (index.get("params") or {}).get("method")
    if method is None and records:
        method = (records[0].get("params") or {}).get("method")
    score_higher_is_better = (method or "tfidf") != "yake"

    graph = build_bipartite_graph(
        records, score_higher_is_better=score_higher_is_better
    )
    communities = _detect_communities(
        graph, algorithm=algorithm, resolution=resolution, seed=seed
    )
    clusters, orphans = partition_clusters(
        graph, communities, min_cluster_papers=min_cluster_papers
    )

    n_papers = sum(
        1 for _, d in graph.nodes(data=True) if d.get("bipartite") == "paper"
    )
    n_terms = sum(
        1 for _, d in graph.nodes(data=True) if d.get("bipartite") == "term"
    )
    params = {
        "algorithm": algorithm,
        "resolution": resolution,
        "min_cluster_papers": min_cluster_papers,
        "seed": seed,
        "phrase_method": method,
        "score_higher_is_better": score_higher_is_better,
    }
    summary = {
        "step": 3,
        "corpus_dir": str(corpus_dir.resolve()),
        "phrases_dir": str(phrases_dir_for_corpus(corpus_dir).resolve()),
        "clusters_dir": str(clusters_dir_for_corpus(corpus_dir).resolve()),
        "params": params,
        "paper_count": n_papers,
        "term_count": n_terms,
        "edge_count": graph.number_of_edges(),
        "community_count": len(communities),
        "cluster_count": len(clusters),
        "orphan_paper_count": orphans["paper_count"],
        "orphan_term_count": orphans["term_count"],
        "elapsed_s": round(time.perf_counter() - t0, 4),
    }

    out_dir = clusters_dir_for_corpus(corpus_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    clusters_path = Path(out_dir, "clusters.json")
    orphans_path = Path(out_dir, "orphans.json")
    graph_path = Path(out_dir, "graph_summary.json")

    with open(clusters_path, "w", encoding="utf-8") as handle:
        json.dump(
            {"step": 3, "params": params, "clusters": clusters},
            handle,
            indent=2,
            ensure_ascii=False,
        )
    with open(orphans_path, "w", encoding="utf-8") as handle:
        json.dump({"step": 3, "params": params, **orphans}, handle, indent=2, ensure_ascii=False)
    with open(graph_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                **summary,
                "clusters_path": str(clusters_path.resolve()),
                "orphans_path": str(orphans_path.resolve()),
            },
            handle,
            indent=2,
            ensure_ascii=False,
        )

    return {
        **summary,
        "clusters": clusters,
        "orphans": orphans,
        "clusters_path": str(clusters_path.resolve()),
        "orphans_path": str(orphans_path.resolve()),
        "graph_summary_path": str(graph_path.resolve()),
    }


def load_clusters(corpus_dir: Path) -> Optional[Dict[str, Any]]:
    """Load ``clusters/clusters.json`` if present."""
    path = Path(corpus_dir, "clusters", "clusters.json")
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_orphans(corpus_dir: Path) -> Optional[Dict[str, Any]]:
    """Load ``clusters/orphans.json`` if present."""
    path = Path(corpus_dir, "clusters", "orphans.json")
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_graph_summary(corpus_dir: Path) -> Optional[Dict[str, Any]]:
    """Load ``clusters/graph_summary.json`` if present."""
    path = Path(corpus_dir, "clusters", "graph_summary.json")
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
