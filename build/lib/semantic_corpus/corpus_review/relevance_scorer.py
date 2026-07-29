"""Relevance scoring for corpus paper selection (metadata-first)."""

from typing import Any, Dict, List, Tuple

from semantic_corpus.corpus_review.constants import (
    HEALTH_TERMS,
    INDIA_LOCATION_TERMS,
    POLLUTANT_TERMS,
)


def _text_blob(metadata: Dict[str, Any]) -> str:
    title = metadata.get("title") or ""
    abstract = metadata.get("abstract") or metadata.get("abstracttext") or ""
    journal = metadata.get("journal") or ""
    authors = metadata.get("authors") or []
    if isinstance(authors, list):
        author_text = " ".join(str(a) for a in authors)
    else:
        author_text = str(authors)
    return " ".join([title, abstract, journal, author_text]).lower()


def _find_matching_terms(text: str, terms: Tuple[str, ...]) -> List[str]:
    found: List[str] = []
    for term in terms:
        if term in text:
            found.append(term)
    return found


def score_paper_relevance(
    metadata: Dict[str, Any],
    *,
    has_xml: bool = False,
    has_pdf: bool = False,
) -> Tuple[int, Dict[str, List[str]]]:
    """Score paper relevance for AQI-in-India corpora.

    Returns (score, matched_terms dict with location_terms, pollutant_terms, health_terms).
    Score prioritizes human review; it does not auto-include or exclude.
    """
    text = _text_blob(metadata)
    title_lower = (metadata.get("title") or "").lower()

    location_terms = _find_matching_terms(text, INDIA_LOCATION_TERMS)
    pollutant_terms = _find_matching_terms(text, POLLUTANT_TERMS)
    health_terms = _find_matching_terms(text, HEALTH_TERMS)

    score = 0

    if "air quality index" in title_lower or " aqi" in title_lower or title_lower.startswith("aqi"):
        score += 3
    elif any(t in title_lower for t in ("air pollution", "pm2.5", "pm10", "particulate")):
        score += 2

    if location_terms:
        score += 2
    else:
        score -= 3

    if pollutant_terms:
        score += 2

    if health_terms:
        score += 1

    if has_xml:
        score += 1
    if has_pdf:
        score += 1

    if metadata.get("doi") and metadata.get("journal"):
        score += 1

    abstract = metadata.get("abstract") or metadata.get("abstracttext") or ""
    if not abstract.strip() and not has_xml and not has_pdf:
        score -= 2

    return score, {
        "location_terms": location_terms,
        "pollutant_terms": pollutant_terms,
        "health_terms": health_terms,
    }
