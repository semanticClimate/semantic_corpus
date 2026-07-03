"""Review table schema and row validation."""

from typing import Any, Dict, List

from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.constants import (
    DEFAULT_REVIEW_STATUS,
    REVIEW_TABLE_COLUMNS,
    VALID_REVIEW_STATUSES,
)


def make_review_row(
    *,
    paper_id: str,
    metadata: Dict[str, Any],
    score: int,
    location_terms: List[str],
    pollutant_terms: List[str],
    health_terms: List[str],
    has_xml: bool,
    has_pdf: bool,
    query_name: str = "",
    query_string: str = "",
    review_status: str = DEFAULT_REVIEW_STATUS,
    review_notes: str = "",
) -> Dict[str, Any]:
    """Build one review table row conforming to REVIEW_TABLE_COLUMNS."""
    authors = metadata.get("authors") or []
    if isinstance(authors, list):
        authors_str = "; ".join(str(a) for a in authors)
    else:
        authors_str = str(authors)

    abstract = metadata.get("abstract") or metadata.get("abstracttext") or ""
    snippet = abstract[:200] + ("..." if len(abstract) > 200 else "")

    row = {
        "review_status": review_status,
        "score": score,
        "paper_id": paper_id,
        "pmcid": metadata.get("pmcid") or "",
        "pmid": metadata.get("pmid") or "",
        "doi": metadata.get("doi") or "",
        "title": metadata.get("title") or "",
        "publication_date": metadata.get("publication_date") or "",
        "journal": metadata.get("journal") or "",
        "authors": authors_str,
        "has_xml": has_xml,
        "has_pdf": has_pdf,
        "query_name": query_name,
        "query_string": query_string,
        "location_terms": ", ".join(location_terms),
        "pollutant_terms": ", ".join(pollutant_terms),
        "health_terms": ", ".join(health_terms),
        "abstract_snippet": snippet,
        "review_notes": review_notes,
    }
    validate_review_row(row)
    return row


def validate_review_row(row: Dict[str, Any]) -> None:
    """Validate a review row has required keys and valid review_status."""
    for col in REVIEW_TABLE_COLUMNS:
        if col not in row:
            raise CorpusError(f"Review row missing column: {col}")
    status = row["review_status"]
    if status not in VALID_REVIEW_STATUSES:
        raise CorpusError(
            f"Invalid review_status {status!r}; expected one of {VALID_REVIEW_STATUSES}"
        )


def filter_rows_by_status(
    rows: List[Dict[str, Any]], status: str
) -> List[Dict[str, Any]]:
    """Return rows matching review_status."""
    return [r for r in rows if r.get("review_status") == status]
