"""Unsupervised clustering of papers using scikit-learn (TF-IDF + KMeans)."""

from typing import Dict, List

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


def _has_content(texts: List[str]) -> bool:
    return any(text and text.strip() for text in texts)


def cluster_documents(
    documents: Dict[str, str],
    *,
    n_clusters: int = 5,
    seed: int = 42,
) -> Dict[str, int]:
    """Cluster documents into groups by TF-IDF cosine similarity.

    Args:
        documents: Mapping of document id to raw text.
        n_clusters: Desired number of clusters (clamped to number of documents).
        seed: Random seed for reproducible KMeans initialization.

    Returns:
        Mapping of document id to cluster index (0-based).
    """
    doc_ids = sorted(documents.keys())
    if not doc_ids:
        return {}

    texts = [documents[doc_id] for doc_id in doc_ids]
    if not _has_content(texts):
        return {doc_id: 0 for doc_id in doc_ids}

    k = max(1, min(n_clusters, len(doc_ids)))
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(texts)

    model = KMeans(n_clusters=k, random_state=seed, n_init=10)
    labels = model.fit_predict(matrix)
    return {doc_id: int(label) for doc_id, label in zip(doc_ids, labels)}


def top_terms_per_cluster(
    documents: Dict[str, str],
    assignments: Dict[str, int],
    *,
    top_n: int = 6,
) -> Dict[int, List[str]]:
    """Return the most representative terms for each cluster.

    Uses the mean TF-IDF weight of each term across a cluster's member
    documents.

    Args:
        documents: Mapping of document id to raw text.
        assignments: Mapping of document id to cluster index.
        top_n: Number of top terms to return per cluster.

    Returns:
        Mapping of cluster index to a list of top terms.
    """
    doc_ids = sorted(documents.keys())
    texts = [documents[doc_id] for doc_id in doc_ids]
    if not doc_ids or not _has_content(texts):
        return {}

    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    result: Dict[int, List[str]] = {}
    clusters = sorted(set(assignments.get(doc_id, 0) for doc_id in doc_ids))
    for cluster_index in clusters:
        row_indices = [
            i for i, doc_id in enumerate(doc_ids)
            if assignments.get(doc_id, 0) == cluster_index
        ]
        if not row_indices:
            continue
        mean_weights = matrix[row_indices].mean(axis=0)
        mean_array = mean_weights.A1 if hasattr(mean_weights, "A1") else mean_weights
        ranked = sorted(
            range(len(feature_names)),
            key=lambda idx: (-float(mean_array[idx]), feature_names[idx]),
        )
        result[cluster_index] = [feature_names[idx] for idx in ranked[:top_n]]
    return result
