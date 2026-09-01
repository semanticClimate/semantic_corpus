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


def handle_from_conicet_url(url_or_id: str) -> str:
    """Extracts the handle linked to each item Ipermanente identifier in DSpace) and evaluates it. / replaced by _ to
        avoid problems in Windows/Linux.
        Eg: 'https://ri.conicet.gov.ar/handle/11336/12345' -> '11336_12345'
        """
    match = re.search(r'11336[/_](\d+)', url_or_id)
    if match:
        return f"conicet_11336_{match.group(1)}"
    return sanitize_paper_id(url_or_id)

def id_from_uba_url(url_or_id: str) -> str:
    """Extracts id and collection from a document in UBA repositories (Exactas, FAUBA).
    E.g.:
    - 'https://bibliotecadigital.exactas.uba.ar/collection/tesis/document/tesis_n5582_DiFiori' -> 'uba_exactas_tesis_tesis_n5582_DiFiori'
    - 'https://ri.agro.uba.ar/greenstone3/library/collection/ti/document/cd620' -> 'uba_fauba_ti_cd620'
    """
    if "exactas.uba.ar" in url_or_id:
        match = re.search(r"/collection/([^/]+)/document/([^/?#;]+)", url_or_id)
        if match:
            return sanitize_paper_id(f"uba_exactas_{match.group(1)}_{match.group(2)}")
    elif "agro.uba.ar" in url_or_id:
        match = re.search(r"/collection/([^/]+)/document/([^/?#;]+)", url_or_id)
        if match:
            return sanitize_paper_id(f"uba_fauba_{match.group(1)}_{match.group(2)}")

    return sanitize_paper_id(url_or_id if url_or_id.startswith("uba_") else f"uba_{url_or_id}")


def id_from_usp_url(url_or_id: str) -> str:
    """Extracts id from a document in USP repository (BDPI / ReP USP).
    E.g.:
    - 'https://repositorio.usp.br/item/002305632' -> 'usp_002305632'
    - 'https://repositorio.usp.br/direct/002305632' -> 'usp_002305632'
    - 'http://dedalus.usp.br/F/?func=direct&doc_number=002305632' -> 'usp_002305632'
    - '002305632' -> 'usp_002305632'
    - 'usp_002305632' -> 'usp_002305632'
    """
    if not url_or_id:
        return ""
    # Matches /item/<id> or /direct/<id>
    match = re.search(r"/(?:item|direct)/([a-zA-Z0-9_\-]+)", url_or_id)
    if match:
        return sanitize_paper_id(f"usp_{match.group(1)}")
    # Matches Dedalus doc_number
    match_dedalus = re.search(r"doc_number=([a-zA-Z0-9_\-]+)", url_or_id)
    if match_dedalus:
        return sanitize_paper_id(f"usp_{match_dedalus.group(1)}")
    # If already starts with usp_
    if url_or_id.startswith("usp_"):
        return sanitize_paper_id(url_or_id)
    return sanitize_paper_id(f"usp_{url_or_id}")