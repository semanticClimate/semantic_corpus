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


def id_from_uchile_url(url_or_id: str) -> str:
    """Extracts handle identifier from a document in Universidad de Chile repository.
    E.g.:
    - 'https://repositorio.uchile.cl/handle/2250/110429' -> 'uchile_2250_110429'
    - '2250/110429' -> 'uchile_2250_110429'
    - '110429' -> 'uchile_2250_110429'
    - 'uchile_2250_110429' -> 'uchile_2250_110429'
    """
    if not url_or_id:
        return ""
    # Matches handle with 2250 prefix (or 2250_...)
    match_2250 = re.search(r"2250[/_](\d+)", url_or_id)
    if match_2250:
        return sanitize_paper_id(f"uchile_2250_{match_2250.group(1)}")
    # Matches generic handle /handle/<prefix>/<id>
    match_handle = re.search(r"/handle/(\d+(?:\.\d+)?)/(\d+)", url_or_id)
    if match_handle:
        prefix = match_handle.group(1).replace(".", "_")
        return sanitize_paper_id(f"uchile_{prefix}_{match_handle.group(2)}")
    # If already starts with uchile_
    if url_or_id.startswith("uchile_"):
        return sanitize_paper_id(url_or_id)
    # If numeric only, assume default 2250 prefix
    if url_or_id.isdigit():
        return sanitize_paper_id(f"uchile_2250_{url_or_id}")
    return sanitize_paper_id(f"uchile_{url_or_id}")


def handle_from_uchile_url(url_or_id: str) -> str:
    """Alias for id_from_uchile_url."""
    return id_from_uchile_url(url_or_id)


def id_from_kerwa_url(url_or_id: str) -> str:
    """Extracts handle identifier from a document in Kerwa (Universidad de Costa Rica) repository.
    E.g.:
    - 'https://www.kerwa.ucr.ac.cr/handle/10669/12345' -> 'kerwa_10669_12345'
    - 'https://hdl.handle.net/10669/12345' -> 'kerwa_10669_12345'
    - '10669/12345' -> 'kerwa_10669_12345'
    - '12345' -> 'kerwa_10669_12345'
    - 'kerwa_10669_12345' -> 'kerwa_10669_12345'
    """
    if not url_or_id:
        return ""
    # Matches handle with 10669 prefix (or 10669_...)
    match_10669 = re.search(r"10669[/_](\d+)", url_or_id)
    if match_10669:
        return sanitize_paper_id(f"kerwa_10669_{match_10669.group(1)}")
    # Matches generic handle /handle/<prefix>/<id>
    match_handle = re.search(r"/handle/(\d+(?:\.\d+)?)/(\d+)", url_or_id)
    if match_handle:
        prefix = match_handle.group(1).replace(".", "_")
        return sanitize_paper_id(f"kerwa_{prefix}_{match_handle.group(2)}")
    # If already starts with kerwa_
    if url_or_id.startswith("kerwa_"):
        return sanitize_paper_id(url_or_id)
    # If numeric only, assume default 10669 prefix
    if url_or_id.isdigit():
        return sanitize_paper_id(f"kerwa_10669_{url_or_id}")
    return sanitize_paper_id(f"kerwa_{url_or_id}")


def handle_from_kerwa_url(url_or_id: str) -> str:
    """Alias for id_from_kerwa_url."""
    return id_from_kerwa_url(url_or_id)


def id_from_unam_url(url_or_id: str) -> str:
    """Extracts identifier from a document in UNAM repository (repositorio.unam.mx).
    E.g.:
    - 'https://repositorio.unam.mx/contenidos/45182' -> 'unam_45182'
    - 'https://repositorio.unam.mx/contenidos/ficha/clima-escolar-45182' -> 'unam_45182'
    - '45182' -> 'unam_45182'
    - 'unam_45182' -> 'unam_45182'
    """
    if not url_or_id:
        return ""
    # Matches /contenidos/(?:ficha/.*-)?(\d+)
    match_contenidos = re.search(r"/contenidos/(?:ficha/.*?-)?(\d+)", url_or_id)
    if match_contenidos:
        return sanitize_paper_id(f"unam_{match_contenidos.group(1)}")
    # Matches handle /handle/<prefix>/<id> or handle.net/<prefix>/<id>
    match_handle = re.search(r"(?:/handle/|handle\.net/)([\d.]+)/(\d+)", url_or_id)
    if match_handle:
        prefix = match_handle.group(1).replace(".", "_")
        return sanitize_paper_id(f"unam_{prefix}_{match_handle.group(2)}")
    # If already starts with unam_
    if url_or_id.startswith("unam_"):
        return sanitize_paper_id(url_or_id)
    # If numeric only, assume default unam item id
    if url_or_id.isdigit():
        return sanitize_paper_id(f"unam_{url_or_id}")
    return sanitize_paper_id(f"unam_{url_or_id}")


def handle_from_unam_url(url_or_id: str) -> str:
    """Alias for id_from_unam_url."""
    return id_from_unam_url(url_or_id)


def id_from_unal_colombia_url(url_or_id: str) -> str:
    """Extracts identifier from a document in Universidad Nacional de Colombia repository (repositorio.unal.edu.co).
    E.g.:
    - 'https://repositorio.unal.edu.co/handle/unal/90677' -> 'unal_colombia_90677'
    - 'https://repositorio.unal.edu.co/items/44fc646d-bbad-4be9-b008-0147830d0039' -> 'unal_colombia_44fc646d_bbad_4be9_b008_0147830d0039'
    - 'https://hdl.handle.net/unal/90677' -> 'unal_colombia_90677'
    - 'unal/90677' -> 'unal_colombia_90677'
    - '90677' -> 'unal_colombia_90677'
    - 'unal_colombia_90677' -> 'unal_colombia_90677'
    - 'unal_90677' -> 'unal_colombia_90677'
    """
    if not url_or_id:
        return ""
    # Matches handle with unal prefix: /handle/unal/(\d+) or unal/(\d+) or unal_(\d+)
    match_unal = re.search(r"unal(?:_colombia)?[/_](\d+)", url_or_id, re.IGNORECASE)
    if match_unal:
        return sanitize_paper_id(f"unal_colombia_{match_unal.group(1)}")
    # Matches DSpace 7 item UUID: /items/([a-f0-9\-]{36})
    match_uuid = re.search(r"/items/([a-f0-9\-]{36})", url_or_id, re.IGNORECASE)
    if match_uuid:
        return sanitize_paper_id(f"unal_colombia_{match_uuid.group(1)}")
    # Matches bare UUID
    if re.match(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", url_or_id, re.IGNORECASE):
        return sanitize_paper_id(f"unal_colombia_{url_or_id}")
    # Matches generic handle /handle/<prefix>/<id> or handle.net/<prefix>/<id>
    match_handle = re.search(r"(?:/handle/|handle\.net/)([\w.]+)/(\w+)", url_or_id)
    if match_handle:
        prefix = match_handle.group(1).replace(".", "_")
        if prefix.lower() == "unal":
            return sanitize_paper_id(f"unal_colombia_{match_handle.group(2)}")
        return sanitize_paper_id(f"unal_colombia_{prefix}_{match_handle.group(2)}")
    # If already starts with unal_colombia_
    if url_or_id.startswith("unal_colombia_"):
        return sanitize_paper_id(url_or_id)
    if url_or_id.startswith("unal_"):
        return sanitize_paper_id(f"unal_colombia_{url_or_id[5:]}")
    # If numeric only, assume default unal item id
    if url_or_id.isdigit():
        return sanitize_paper_id(f"unal_colombia_{url_or_id}")
    return sanitize_paper_id(f"unal_colombia_{url_or_id}")


def handle_from_unal_colombia_url(url_or_id: str) -> str:
    """Alias for id_from_unal_colombia_url."""
    return id_from_unal_colombia_url(url_or_id)


def id_from_unal_url(url_or_id: str) -> str:
    """Alias for id_from_unal_colombia_url."""
    return id_from_unal_colombia_url(url_or_id)


def handle_from_unal_url(url_or_id: str) -> str:
    """Alias for id_from_unal_colombia_url."""
    return id_from_unal_colombia_url(url_or_id)



