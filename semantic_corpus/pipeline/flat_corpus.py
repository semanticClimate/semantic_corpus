"""Flat workdir layout: typed filenames with transformation-history suffixes.

All artifacts live under ``--workdir`` (no ``downloads/``, no ``temp/queries/``,
no ``data/documents/{fmt}/`` nesting for new collects).

Naming (history reads left → right)::

    {id}.json       metadata / abstract (JSON stream)
    {id}.xml        publisher / EPMC fullTextXML
    {id}.pdf        native PDF
    {id}.pdf.xml    Docling PDF → XML
    {id}.pdf.html   Docling PDF → HTML
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from semantic_corpus.repositories.document_content import (
    is_valid_document_file,
    looks_like_fulltext_xml,
    looks_like_pdf,
)

_PMC_RE = re.compile(r"(PMC\d+)", re.IGNORECASE)


def paper_stem(paper_id: str) -> str:
    """Stable filename stem, preferring ``PMC123`` over prefixed ids."""
    text = str(paper_id or "").strip()
    if not text:
        return "unknown"
    match = _PMC_RE.search(text)
    if match:
        return match.group(1).upper()
    safe = re.sub(r"[^\w.\-]+", "_", text).strip("_")
    return safe or "unknown"


def is_flat_corpus(workdir: Path) -> bool:
    """True when workdir holds flat paper files (no BAGIT required)."""
    workdir = Path(workdir)
    if path_search_results(workdir).is_file():
        return True
    if any(workdir.glob("PMC*.json")):
        return True
    if any(workdir.glob("*.xml")) or any(workdir.glob("*.pdf")):
        return True
    return False


def list_flat_paper_ids(workdir: Path) -> List[str]:
    """Paper ids from search_results.json or flat ``{id}.json`` files."""
    ids = list_paper_ids_from_search(workdir)
    if ids:
        return ids
    workdir = Path(workdir)
    seen = set()
    out: List[str] = []
    for path in sorted(workdir.glob("*.json")):
        name = path.name
        if name in {"query.json", "search_results.json"}:
            continue
        if name.endswith("_metadata.json"):
            stem = name[: -len("_metadata.json")]
        else:
            stem = path.stem
        # Skip transform sidecars mistakenly named *.json
        if "." in stem:
            continue
        stem = paper_stem(stem)
        if stem and stem not in seen and stem != "unknown":
            seen.add(stem)
            out.append(stem)
    return out


def path_json(workdir: Path, paper_id: str) -> Path:
    return Path(workdir) / f"{paper_stem(paper_id)}.json"


def path_xml(workdir: Path, paper_id: str) -> Path:
    return Path(workdir) / f"{paper_stem(paper_id)}.xml"


def path_pdf(workdir: Path, paper_id: str) -> Path:
    return Path(workdir) / f"{paper_stem(paper_id)}.pdf"


def path_pdf_xml(workdir: Path, paper_id: str) -> Path:
    """Docling-derived XML from PDF (``{id}.pdf.xml``)."""
    return Path(workdir) / f"{paper_stem(paper_id)}.pdf.xml"


def path_pdf_html(workdir: Path, paper_id: str) -> Path:
    return Path(workdir) / f"{paper_stem(paper_id)}.pdf.html"


def path_query(workdir: Path) -> Path:
    return Path(workdir) / "query.json"


def path_search_results(workdir: Path) -> Path:
    return Path(workdir) / "search_results.json"


def find_native_xml(workdir: Path, paper_id: str) -> Optional[Path]:
    path = path_xml(workdir, paper_id)
    if is_valid_document_file(path, "xml"):
        return path
    return None


def find_pdf(workdir: Path, paper_id: str) -> Optional[Path]:
    path = path_pdf(workdir, paper_id)
    if is_valid_document_file(path, "pdf"):
        return path
    return None


def find_pdf_xml(workdir: Path, paper_id: str) -> Optional[Path]:
    path = path_pdf_xml(workdir, paper_id)
    if path.is_file() and looks_like_fulltext_xml(path.read_bytes()[:4096]):
        return path
    # Also accept if full file validates as xml-ish
    if is_valid_document_file(path, "xml"):
        return path
    return None


def find_best_xml(workdir: Path, paper_id: str) -> Optional[Path]:
    """Prefer publisher XML, then Docling ``.pdf.xml``."""
    return find_native_xml(workdir, paper_id) or find_pdf_xml(workdir, paper_id)


def find_paper_json(workdir: Path, paper_id: str) -> Optional[Path]:
    path = path_json(workdir, paper_id)
    if path.is_file() and path.stat().st_size > 0:
        head = path.read_bytes()[:1]
        if head == b"{":
            return path
    return None


def load_paper_json(workdir: Path, paper_id: str) -> Dict[str, Any]:
    path = find_paper_json(workdir, paper_id)
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def paper_done_enough(workdir: Path, paper_id: str) -> bool:
    """Resume-friendly: metadata JSON plus any usable text source."""
    if find_paper_json(workdir, paper_id) is None:
        return False
    if find_best_xml(workdir, paper_id) is not None:
        return True
    meta = load_paper_json(workdir, paper_id)
    abstract = str(
        meta.get("abstract") or meta.get("abstractText") or meta.get("abstracttext") or ""
    ).strip()
    return bool(abstract)


def list_paper_ids_from_search(workdir: Path) -> List[str]:
    path = path_search_results(workdir)
    if not path.is_file():
        return []
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(rows, list):
        return []
    ids: List[str] = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        raw = (
            row.get("pmcid")
            or row.get("paper_id")
            or row.get("pmid")
            or ""
        )
        stem = paper_stem(str(raw))
        if stem and stem not in seen and stem != "unknown":
            seen.add(stem)
            ids.append(stem)
    return ids


def write_json_atomic(path: Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(text, encoding="utf-8")
    partial.replace(path)
