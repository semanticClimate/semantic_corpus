"""Helpers for stable repository paper identifiers and filenames."""

import hashlib
import re
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse


def sanitize_paper_id(paper_id: str) -> str:
    """Return a filesystem-safe identifier."""
    safe = paper_id.strip()
    safe = safe.replace("https://doi.org/", "")
    safe = safe.replace("https://openalex.org/", "")
    safe = re.sub(r"[^\w.\-]+", "_", safe)
    return safe.strip("_") or "unknown"


def get_result_paper_id(paper: Dict[str, Any]) -> Optional[str]:
    """Pick the best download identifier from a search result record."""
    if paper.get("paper_id"):
        return str(paper["paper_id"])
    for key in ("pmcid", "arxiv_id", "openalex_id", "doi", "pmid", "pid", "url"):
        value = paper.get(key)
        if value:
            return str(value)
    return None


def openalex_short_id(openalex_id: str) -> str:
    """Normalize OpenAlex work IDs to W1234567890 form."""
    if not openalex_id:
        return ""
    if openalex_id.startswith("https://openalex.org/"):
        return openalex_id.rsplit("/", 1)[-1]
    return openalex_id


def pid_from_scielo_url(url: str) -> str:
    """Extract SciELO pid query parameter from an article URL."""
    query = parse_qs(urlparse(url).query)
    pid_values = query.get("pid") or []
    return pid_values[0] if pid_values else ""


def id_from_redalyc_url(url: str) -> str:
    """Extract Redalyc numeric article id from an article URL."""
    query = parse_qs(urlparse(url).query)
    id_values = query.get("id") or []
    if id_values:
        return id_values[0]
    match = re.search(r"/(\d+)\.pdf$", url)
    if match:
        return match.group(1)
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
