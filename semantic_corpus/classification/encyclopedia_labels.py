"""Load climate encyclopedia wordlists as labeled category vocabularies.

The ../encyclopedia project produces curated wordlist CSV files
(``term,count,manual_delete``). Each wordlist is treated as one supervised
category whose vocabulary is used to tag papers.
"""

import csv
from pathlib import Path
from typing import Dict, List, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from semantic_corpus.core.exceptions import CorpusError

CURATED_WORDLIST_GLOB = "**/*_curated.csv"
RAW_WORDLIST_GLOB = "**/raw_wordlist.csv"
MANUAL_DELETE_YES = "yes"

# Generic directory names that do not make good category labels.
_GENERIC_DIR_NAMES = frozenset(
    {"temp", "tmp", "docs", "scripts", "test", "tests", "output", "outputs", "data"}
)


def _category_name_from_path(path: Path, encyclopedia_dir: Path) -> str:
    """Derive a readable category name from a wordlist file path.

    Prefers the first meaningful ancestor directory (e.g. ``ipcc``) over
    run-specific folders such as ``phase1_syr_full_top1000_countgt1``.
    """
    try:
        relative = path.relative_to(encyclopedia_dir)
    except ValueError:
        relative = path
    parts = [part for part in relative.parts[:-1] if part not in _GENERIC_DIR_NAMES]
    name = parts[0] if parts else (relative.parent.name or relative.stem)
    return name.replace("-", "_")


def load_wordlist_terms(csv_path: Path, *, min_count: int = 1) -> List[str]:
    """Load non-deleted terms from a curated wordlist CSV.

    Args:
        csv_path: Path to a ``term,count,manual_delete`` CSV.
        min_count: Minimum count for a term to be included.

    Returns:
        Lowercased terms, longest first (so multi-word terms match first).
    """
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise CorpusError(f"Wordlist CSV not found: {csv_path}")

    terms: List[str] = []
    with open(csv_path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            term = (record.get("term") or "").strip()
            if not term:
                continue
            if (record.get("manual_delete") or "").strip().lower() == MANUAL_DELETE_YES:
                continue
            try:
                count = int(record.get("count") or 0)
            except ValueError:
                count = 0
            if count < min_count:
                continue
            terms.append(term.lower())

    terms.sort(key=lambda t: (-len(t), t))
    return terms


def load_encyclopedia_categories(
    encyclopedia_dir: Path,
    *,
    min_count: int = 2,
    max_terms_per_category: int = 400,
) -> Dict[str, List[str]]:
    """Discover encyclopedia wordlists and return category -> terms.

    Prefers curated wordlists; falls back to raw wordlists when no curated
    files are present.

    Args:
        encyclopedia_dir: Root of the encyclopedia project (e.g. ../encyclopedia).
        min_count: Minimum term count to include.
        max_terms_per_category: Cap on terms kept per category.

    Returns:
        Mapping of category name to a list of vocabulary terms.
    """
    encyclopedia_dir = Path(encyclopedia_dir)
    if not encyclopedia_dir.is_dir():
        raise CorpusError(f"Encyclopedia directory not found: {encyclopedia_dir}")

    wordlist_paths = sorted(encyclopedia_dir.glob(CURATED_WORDLIST_GLOB))
    if not wordlist_paths:
        wordlist_paths = sorted(encyclopedia_dir.glob(RAW_WORDLIST_GLOB))

    categories: Dict[str, List[str]] = {}
    for path in wordlist_paths:
        terms = load_wordlist_terms(path, min_count=min_count)
        if not terms:
            continue
        name = _category_name_from_path(path, encyclopedia_dir)
        existing = categories.setdefault(name, [])
        for term in terms:
            if term not in existing:
                existing.append(term)
        categories[name] = existing[:max_terms_per_category]

    if not categories:
        raise CorpusError(
            f"No usable wordlists found under {encyclopedia_dir} "
            f"(looked for {CURATED_WORDLIST_GLOB} then {RAW_WORDLIST_GLOB})"
        )
    return categories


def classify_by_vocabularies(
    documents: Dict[str, str],
    categories: Dict[str, Sequence[str]],
    *,
    min_score: float = 0.03,
    max_matched_terms: int = 8,
) -> Dict[str, Dict[str, object]]:
    """Assign each document to its nearest category by TF-IDF cosine similarity.

    A supervised nearest-centroid classifier: each curated climate encyclopedia
    vocabulary is joined into a category "document", vectorized with the same
    TF-IDF space as the papers, and each paper is assigned to the most similar
    category.

    Args:
        documents: Mapping of document id to raw text.
        categories: Mapping of category name to vocabulary terms.
        min_score: Minimum cosine similarity to assign a category.
        max_matched_terms: Cap on matched terms recorded per document.

    Returns:
        Mapping of document id to a result dict with keys ``category``,
        ``score``, ``matched_terms``, and ``all_scores``.
    """
    doc_ids = sorted(documents.keys())
    category_names = sorted(categories.keys())

    empty = {
        doc_id: {"category": "", "score": 0.0, "matched_terms": [], "all_scores": {}}
        for doc_id in doc_ids
    }
    if not doc_ids or not category_names:
        return empty

    doc_texts = [documents[doc_id] for doc_id in doc_ids]
    category_texts = [" ".join(categories[name]) for name in category_names]

    if not any(text and text.strip() for text in doc_texts):
        return empty

    vectorizer = TfidfVectorizer(stop_words="english")
    vectorizer.fit(doc_texts + category_texts)
    doc_matrix = vectorizer.transform(doc_texts)
    category_matrix = vectorizer.transform(category_texts)

    similarities = cosine_similarity(doc_matrix, category_matrix)

    results: Dict[str, Dict[str, object]] = {}
    for row_index, doc_id in enumerate(doc_ids):
        row = similarities[row_index]
        all_scores = {
            category_names[col]: round(float(row[col]), 4)
            for col in range(len(category_names))
        }
        best_col = int(row.argmax())
        best_score = float(row[best_col])

        if best_score < min_score:
            results[doc_id] = {
                "category": "",
                "score": 0.0,
                "matched_terms": [],
                "all_scores": all_scores,
            }
            continue

        best_category = category_names[best_col]
        text_lower = (documents[doc_id] or "").lower()
        matched_terms = [
            term for term in categories[best_category] if term in text_lower
        ][:max_matched_terms]
        results[doc_id] = {
            "category": best_category,
            "score": round(best_score, 4),
            "matched_terms": matched_terms,
            "all_scores": all_scores,
        }
    return results
