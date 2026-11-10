"""BagIt-friendly corpus paths: ``data/packets/`` map + tag files at workdir root.

Naming (history reads left → right)::

    {id}.json       metadata / abstract (JSON stream)
    {id}.xml        publisher / EPMC fullTextXML
    {id}.pdf        native PDF (lazy; often gitignored)
    {id}.pdf.xml    Docling PDF → XML
    {id}.pdf.html   Docling PDF → HTML

See ``docs/bagit_structure.md``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from semantic_corpus.repositories.document_content import (
    is_valid_document_file,
    looks_like_fulltext_xml,
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


def packets_dir(workdir: Path) -> Path:
    """Map directory for packet bytes (``data/packets/``)."""
    return Path(workdir) / "data" / "packets"


def indexes_dir(workdir: Path) -> Path:
    """Reduce directory (``data/indexes/``)."""
    return Path(workdir) / "data" / "indexes"


def ensure_packets_dir(workdir: Path) -> Path:
    path = packets_dir(workdir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_indexes_dir(workdir: Path) -> Path:
    path = indexes_dir(workdir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def path_query(workdir: Path) -> Path:
    return Path(workdir) / "query.json"


def path_search_results(workdir: Path) -> Path:
    return Path(workdir) / "search_results.json"


def path_corpus_json(workdir: Path) -> Path:
    return Path(workdir) / "corpus.json"


def path_json(workdir: Path, paper_id: str) -> Path:
    return packets_dir(workdir) / f"{paper_stem(paper_id)}.json"


def path_xml(workdir: Path, paper_id: str) -> Path:
    return packets_dir(workdir) / f"{paper_stem(paper_id)}.xml"


def path_pdf(workdir: Path, paper_id: str) -> Path:
    return packets_dir(workdir) / f"{paper_stem(paper_id)}.pdf"


def path_pdf_xml(workdir: Path, paper_id: str) -> Path:
    return packets_dir(workdir) / f"{paper_stem(paper_id)}.pdf.xml"


def path_pdf_html(workdir: Path, paper_id: str) -> Path:
    return packets_dir(workdir) / f"{paper_stem(paper_id)}.pdf.html"


def _candidate_packet_files(workdir: Path, paper_id: str, suffix: str) -> List[Path]:
    """Preferred path plus legacy flat / BAGIT document locations."""
    stem = paper_stem(paper_id)
    workdir = Path(workdir)
    names = [f"{stem}{suffix}"]
    # Legacy prefixed ids in old bags
    if not stem.startswith("europe_pmc_"):
        names.append(f"europe_pmc_{stem}{suffix}")
    out: List[Path] = []
    for name in names:
        out.extend(
            [
                packets_dir(workdir) / name,
                workdir / name,
                workdir / "documents" / name,
                workdir / "data" / "documents" / name,
                workdir
                / "data"
                / "documents"
                / suffix.lstrip(".").split(".")[0]
                / name,
            ]
        )
    # Legacy per-format dirs for .xml / .pdf / .html
    kind = suffix.lstrip(".").split(".")[0]
    if kind in {"xml", "pdf", "html", "json"}:
        for name in names:
            out.append(workdir / "data" / "documents" / kind / name)
            out.append(workdir / "data" / "data" / "documents" / kind / name)
    return out


def _find_valid(workdir: Path, paper_id: str, suffix: str, fmt: str) -> Optional[Path]:
    for path in _candidate_packet_files(workdir, paper_id, suffix):
        if fmt == "json":
            if path.is_file() and path.stat().st_size > 0:
                try:
                    if path.read_bytes()[:1] == b"{":
                        return path
                except OSError:
                    continue
        elif is_valid_document_file(path, fmt):
            return path
    return None


def find_native_xml(workdir: Path, paper_id: str) -> Optional[Path]:
    return _find_valid(workdir, paper_id, ".xml", "xml")


def find_pdf(workdir: Path, paper_id: str) -> Optional[Path]:
    return _find_valid(workdir, paper_id, ".pdf", "pdf")


def find_pdf_xml(workdir: Path, paper_id: str) -> Optional[Path]:
    for path in _candidate_packet_files(workdir, paper_id, ".pdf.xml"):
        if not path.is_file():
            continue
        try:
            head = path.read_bytes()[:4096]
        except OSError:
            continue
        if looks_like_fulltext_xml(head) or is_valid_document_file(path, "xml"):
            return path
    return None


def find_best_xml(workdir: Path, paper_id: str) -> Optional[Path]:
    """Prefer publisher XML, then Docling ``.pdf.xml``."""
    return find_native_xml(workdir, paper_id) or find_pdf_xml(workdir, paper_id)


def find_paper_json(workdir: Path, paper_id: str) -> Optional[Path]:
    found = _find_valid(workdir, paper_id, ".json", "json")
    if found is not None:
        return found
    # Legacy ``*_metadata.json``
    stem = paper_stem(paper_id)
    for path in (
        packets_dir(workdir) / f"{stem}_metadata.json",
        Path(workdir) / f"{stem}_metadata.json",
        Path(workdir) / "data" / "metadata" / f"{stem}_metadata.json",
        Path(workdir) / "data" / "metadata" / f"europe_pmc_{stem}_metadata.json",
    ):
        if path.is_file() and path.stat().st_size > 0:
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


def paper_has_text(workdir: Path, paper_id: str) -> bool:
    """True if XML / pdf.xml / abstract can supply phrase text."""
    if find_best_xml(workdir, paper_id) is not None:
        return True
    meta = load_paper_json(workdir, paper_id)
    abstract = str(
        meta.get("abstract")
        or meta.get("abstractText")
        or meta.get("abstracttext")
        or ""
    ).strip()
    return bool(abstract)


def paper_collect_done(workdir: Path, paper_id: str) -> bool:
    """Collect resume: JSON present and XML resolved or definitively unavailable.

    Abstract-only is **not** enough — resume retries XML until success or a
    recorded ``_collect_xml`` miss (``unavailable`` / ``no_pmcid``). PDF is
    never required for collect.
    """
    if find_paper_json(workdir, paper_id) is None:
        return False
    if find_best_xml(workdir, paper_id) is not None:
        return True
    meta = load_paper_json(workdir, paper_id)
    status = str(meta.get("_collect_xml") or "").strip().lower()
    return status in {"unavailable", "no_pmcid", "miss"}


def paper_done_enough(workdir: Path, paper_id: str) -> bool:
    """Alias used by doit ``paper:{id}`` uptodate — same as collect done."""
    return paper_collect_done(workdir, paper_id)


def paper_needs_pdf(workdir: Path, paper_id: str) -> bool:
    return find_pdf(workdir, paper_id) is None


def is_bagit_or_packets_corpus(workdir: Path) -> bool:
    workdir = Path(workdir)
    if (workdir / "bagit.txt").is_file() or (workdir / "data" / "bagit.txt").is_file():
        return True
    if packets_dir(workdir).is_dir() and any(packets_dir(workdir).iterdir()):
        return True
    return is_flat_corpus(workdir)


def is_flat_corpus(workdir: Path) -> bool:
    """True when workdir has search hits or packet-like files (flat or BagIt)."""
    workdir = Path(workdir)
    if path_search_results(workdir).is_file():
        return True
    pkt = packets_dir(workdir)
    if pkt.is_dir() and (
        any(pkt.glob("PMC*.json"))
        or any(pkt.glob("*.xml"))
        or any(pkt.glob("*.pdf"))
    ):
        return True
    if any(workdir.glob("PMC*.json")):
        return True
    if any(workdir.glob("*.xml")) or any(workdir.glob("*.pdf")):
        return True
    return False


def list_paper_ids_from_search(workdir: Path) -> List[str]:
    """Ids for collect tasks: prefer ``pmcid``; fall back to pmid/paper_id.

    PMID-only hits are still listed (metadata/abstract); XML fetch soft-skips
    them when no PMCID can be resolved.
    """
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
        pmcid = str(row.get("pmcid") or "").strip()
        if pmcid:
            stem = paper_stem(pmcid)
        else:
            raw = row.get("paper_id") or row.get("pmid") or row.get("id") or ""
            stem = paper_stem(str(raw))
        if stem and stem not in seen and stem != "unknown":
            seen.add(stem)
            ids.append(stem)
    return ids


def list_flat_paper_ids(workdir: Path) -> List[str]:
    """Paper ids from search_results or packet ``{id}.json`` files."""
    ids = list_paper_ids_from_search(workdir)
    if ids:
        return ids
    workdir = Path(workdir)
    seen = set()
    out: List[str] = []
    roots = [packets_dir(workdir), workdir]
    skip = {"query", "search_results", "corpus"}
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.json")):
            name = path.name
            if name.endswith("_metadata.json"):
                stem = name[: -len("_metadata.json")]
            else:
                stem = path.stem
            if stem in skip or "." in stem:
                continue
            stem = paper_stem(stem)
            if stem and stem not in seen and stem != "unknown":
                seen.add(stem)
                out.append(stem)
    return out


def write_json_atomic(path: Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(text, encoding="utf-8")
    partial.replace(path)


def write_corpus_json(
    workdir: Path,
    *,
    query: Optional[str] = None,
    limit: Optional[int] = None,
    repository: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    path = path_corpus_json(workdir)
    payload: Dict[str, Any] = {
        "layout": "bagit_packets",
        "packets": "data/packets",
        "indexes": "data/indexes",
    }
    if query is not None:
        payload["query"] = query
    if limit is not None:
        payload["limit"] = limit
    if repository is not None:
        payload["repository"] = repository
    if extra:
        payload.update(extra)
    write_json_atomic(path, payload)
    return path


def ensure_light_bagit(workdir: Path) -> None:
    """Ensure minimal BagIt tag files exist (payload under ``data/``)."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "data").mkdir(parents=True, exist_ok=True)
    ensure_packets_dir(workdir)
    ensure_indexes_dir(workdir)
    bagit_txt = workdir / "bagit.txt"
    if not bagit_txt.is_file():
        bagit_txt.write_text(
            "BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n",
            encoding="utf-8",
        )
    bag_info = workdir / "bag-info.txt"
    if not bag_info.is_file():
        bag_info.write_text(
            "Bag-Software: semantic_corpus\n"
            "External-Description: semantic_corpus pipeline corpus\n",
            encoding="utf-8",
        )
