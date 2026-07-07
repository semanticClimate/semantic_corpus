"""Plain-text previews for interactive paper review."""

import html
import re
from pathlib import Path
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from lxml import etree


def strip_markup(text: str) -> str:
    """Remove HTML/XML markup and collapse whitespace."""
    if not text:
        return ""
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _local_name(tag: str) -> str:
    if isinstance(tag, str) and "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return str(tag)


def _element_text(element: etree._Element) -> str:
    return re.sub(r"\s+", " ", "".join(element.itertext())).strip()


def extract_intro_from_xml(xml_path: Path, max_chars: int = 800) -> str:
    """Extract an introduction excerpt from JATS/PMC XML."""
    xml_path = Path(xml_path)
    if not xml_path.is_file():
        return ""

    try:
        root = etree.parse(str(xml_path)).getroot()
    except etree.XMLSyntaxError:
        return ""

    sections = root.findall(".//{*}body//{*}sec")
    intro_parts: list[str] = []

    for section in sections:
        title_elem = section.find(".//{*}title")
        title = _element_text(title_elem) if title_elem is not None else ""
        if title and "intro" not in title.lower():
            continue
        for paragraph in section.findall(".//{*}p"):
            text = _element_text(paragraph)
            if text:
                intro_parts.append(text)
        if intro_parts:
            break

    if not intro_parts:
        for paragraph in root.findall(".//{*}body//{*}p"):
            text = _element_text(paragraph)
            if text:
                intro_parts.append(text)
            if sum(len(part) for part in intro_parts) >= max_chars:
                break

    intro = " ".join(intro_parts)
    if len(intro) > max_chars:
        return intro[: max_chars - 3].rstrip() + "..."
    return intro


def _corpus_document_roots(corpus_dir: Path) -> list[Path]:
    """Return candidate document roots (handles nested data/data/ BAGIT layouts)."""
    roots: list[Path] = []
    for candidate in (corpus_dir / "data", corpus_dir / "data" / "data"):
        if candidate.is_dir():
            roots.append(candidate)
    return roots


def _corpus_file(
    corpus_dir: Path, paper_id: str, pmcid: str, sub: str, ext: str
) -> Optional[Path]:
    """Find a document under corpus data/documents/{sub}/."""
    names: list[str] = []
    if paper_id:
        names.append(paper_id)
    if pmcid:
        names.append(pmcid)
        prefixed = f"europe_pmc_{pmcid}"
        if prefixed not in names:
            names.append(prefixed)
    for root in _corpus_document_roots(corpus_dir):
        for name in names:
            candidate = root / "documents" / sub / f"{name}.{ext}"
            if candidate.is_file():
                return candidate
    return None


def resolve_document_paths(
    row: Dict[str, Any],
    *,
    query_dir: Optional[Path] = None,
    xml_dir: Optional[Path] = None,
    corpus_dir: Optional[Path] = None,
) -> Dict[str, Optional[Path]]:
    """Locate downloaded files for a review row."""
    query_dir = Path(query_dir) if query_dir else None
    xml_dir = Path(xml_dir) if xml_dir else query_dir
    corpus_dir = Path(corpus_dir) if corpus_dir else None

    pmcid = row.get("pmcid") or ""
    paper_id = row.get("paper_id") or ""
    file_stems: list[str] = []
    if pmcid:
        file_stems.append(pmcid)
    if paper_id:
        if paper_id not in file_stems:
            file_stems.append(paper_id)
        short_id = paper_id.replace("europe_pmc_", "")
        if short_id and short_id not in file_stems:
            file_stems.append(short_id)

    xml_path = None
    pdf_path = None
    html_path = None

    for stem in file_stems:
        if xml_dir:
            candidate = Path(xml_dir, f"{stem}.xml")
            if candidate.is_file():
                xml_path = candidate
        if query_dir:
            for ext, target in (("pdf", "pdf_path"), ("html", "html_path")):
                candidate = Path(query_dir, f"{stem}.{ext}")
                if candidate.is_file():
                    if target == "pdf_path":
                        pdf_path = candidate
                    else:
                        html_path = candidate
        if corpus_dir:
            found = _corpus_file(corpus_dir, paper_id, pmcid, "xml", "xml")
            if found:
                xml_path = found
            found = _corpus_file(corpus_dir, paper_id, pmcid, "pdf", "pdf")
            if found:
                pdf_path = found
            found = _corpus_file(corpus_dir, paper_id, pmcid, "html", "html")
            if found:
                html_path = found

    return {
        "xml_path": xml_path,
        "pdf_path": pdf_path,
        "html_path": html_path,
    }


def build_paper_preview(
    row: Dict[str, Any],
    *,
    search_metadata: Optional[Dict[str, Any]] = None,
    query_dir: Optional[Path] = None,
    xml_dir: Optional[Path] = None,
    corpus_dir: Optional[Path] = None,
    intro_max_chars: int = 800,
) -> Dict[str, str]:
    """Build display fields for one review row."""
    metadata = search_metadata or {}
    abstract = strip_markup(
        metadata.get("abstract")
        or row.get("abstract")
        or row.get("abstract_snippet")
        or ""
    )

    paths = resolve_document_paths(
        row,
        query_dir=query_dir,
        xml_dir=xml_dir,
        corpus_dir=corpus_dir,
    )
    intro = ""
    if paths["xml_path"]:
        intro = extract_intro_from_xml(paths["xml_path"], max_chars=intro_max_chars)
    elif paths["html_path"]:
        html_text = paths["html_path"].read_text(encoding="utf-8", errors="ignore")
        intro = strip_markup(html_text)[:intro_max_chars]

    topics = ", ".join(
        part
        for part in (
            row.get("location_terms"),
            row.get("pollutant_terms"),
            row.get("health_terms"),
            row.get("cluster_terms"),
            row.get("encyclopedia_category"),
        )
        if part
    )

    return {
        "abstract": abstract,
        "intro": intro,
        "topics": topics,
        "xml_path": str(paths["xml_path"] or ""),
        "pdf_path": str(paths["pdf_path"] or ""),
    }
