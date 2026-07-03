"""Annotate review rows with unsupervised clusters and encyclopedia categories."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from semantic_corpus.classification.encyclopedia_labels import (
    classify_by_vocabularies,
)
from semantic_corpus.classification.unsupervised import (
    cluster_documents,
    top_terms_per_cluster,
)


def documents_from_review_rows(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """Build id -> text mapping from review rows (title + abstract snippet)."""
    documents: Dict[str, str] = {}
    for row in rows:
        paper_id = row.get("paper_id") or ""
        if not paper_id:
            continue
        text = " ".join(
            [row.get("title") or "", row.get("abstract_snippet") or ""]
        ).strip()
        documents[paper_id] = text
    return documents


def documents_from_search_results(search_results_path: Path) -> Dict[str, str]:
    """Build id -> text mapping from search_results.json (full abstracts)."""
    search_results_path = Path(search_results_path)
    with open(search_results_path, "r", encoding="utf-8") as handle:
        results = json.load(handle)

    documents: Dict[str, str] = {}
    for paper in results:
        pmcid = paper.get("pmcid") or ""
        pmid = paper.get("pmid") or ""
        identifier = pmcid or pmid
        paper_id = f"europe_pmc_{identifier}" if identifier else "europe_pmc_unknown"
        text = " ".join(
            [paper.get("title") or "", paper.get("abstract") or ""]
        ).strip()
        documents[paper_id] = text
    return documents


def annotate_rows_with_clusters(
    rows: List[Dict[str, Any]],
    *,
    documents: Optional[Dict[str, str]] = None,
    n_clusters: int = 5,
    seed: int = 42,
) -> Dict[int, List[str]]:
    """Add cluster_id and cluster_terms to review rows in place.

    Args:
        rows: Review rows to annotate.
        documents: Optional id -> text mapping; built from rows when omitted.
        n_clusters: Desired number of clusters.
        seed: Random seed for reproducibility.

    Returns:
        Mapping of cluster index to representative top terms.
    """
    if documents is None:
        documents = documents_from_review_rows(rows)

    assignments = cluster_documents(
        documents, n_clusters=n_clusters, seed=seed
    )
    cluster_terms = top_terms_per_cluster(documents, assignments)

    for row in rows:
        paper_id = row.get("paper_id") or ""
        if paper_id in assignments:
            cluster_index = assignments[paper_id]
            row["cluster_id"] = str(cluster_index)
            row["cluster_terms"] = ", ".join(cluster_terms.get(cluster_index, []))
        else:
            row["cluster_id"] = ""
            row["cluster_terms"] = ""
    return cluster_terms


def annotate_rows_with_encyclopedia(
    rows: List[Dict[str, Any]],
    categories: Dict[str, Sequence[str]],
    *,
    documents: Optional[Dict[str, str]] = None,
    min_score: float = 0.03,
) -> Dict[str, Dict[str, object]]:
    """Add encyclopedia_category, encyclopedia_score, encyclopedia_terms in place.

    Args:
        rows: Review rows to annotate.
        categories: Mapping of category name to vocabulary terms.
        documents: Optional id -> text mapping; built from rows when omitted.
        min_score: Minimum cosine similarity to assign a category.

    Returns:
        Per-document classification results keyed by paper_id.
    """
    if documents is None:
        documents = documents_from_review_rows(rows)

    results = classify_by_vocabularies(
        documents, categories, min_score=min_score
    )

    for row in rows:
        paper_id = row.get("paper_id") or ""
        result = results.get(paper_id)
        if result:
            row["encyclopedia_category"] = str(result["category"])
            row["encyclopedia_score"] = str(result["score"])
            row["encyclopedia_terms"] = ", ".join(result["matched_terms"])
        else:
            row["encyclopedia_category"] = ""
            row["encyclopedia_score"] = ""
            row["encyclopedia_terms"] = ""
    return results
