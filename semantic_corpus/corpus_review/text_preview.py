"""Plain-text previews for interactive paper review."""

import html
import re
from pathlib import Path
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from lxml import etree
from html import escape


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
            for sub, attr in (("xml", "xml_path"), ("pdf", "pdf_path"), ("html", "html_path")):
                candidate = Path(corpus_dir, "data", "documents", sub, f"{paper_id}.{sub}")
                if candidate.is_file():
                    if attr == "xml_path":
                        xml_path = candidate
                    elif attr == "pdf_path":
                        pdf_path = candidate
                    else:
                        html_path = candidate

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


def render_jats_to_html(xml_path: Path) -> str:
    """Render a JATS/PMC XML file to a simple, readable HTML string.

    The output includes the title, a simple author list, the abstract,
    and body paragraphs. This is intentionally minimal and focuses on
    readability rather than faithful conversion.
    """
    xml_path = Path(xml_path)
    if not xml_path.is_file():
        return ""

    try:
        root = etree.parse(str(xml_path)).getroot()
    except etree.XMLSyntaxError:
        return ""

    def find_text(elem, tag):
        e = elem.find(f".//{{*}}{tag}")
        return _element_text(e) if e is not None else ""

    title = find_text(root, "article-title")

    # Authors: collect contrib/name blocks
    authors = []
    for contrib in root.findall('.//{*}contrib'):
        # only author-type contribs
        ctype = contrib.get("contrib-type")
        if ctype and ctype.lower() != "author":
            continue
        name_el = contrib.find('.//{*}name')
        if name_el is not None:
            authors.append(_element_text(name_el))
        else:
            # fallback to raw contribut text
            text = _element_text(contrib)
            if text:
                authors.append(text)

    # Abstract: may contain multiple paragraphs
    abstract_parts: list[str] = []
    for abstract in root.findall('.//{*}abstract'):
        for p in abstract.findall('.//{*}p'):
            t = _element_text(p)
            if t:
                abstract_parts.append(t)
        if not abstract_parts:
            # direct text fallback
            t = _element_text(abstract)
            if t:
                abstract_parts.append(t)
        if abstract_parts:
            break

    # Body paragraphs
    body_paragraphs: list[str] = []
    for p in root.findall('.//{*}body//{*}p'):
        t = _element_text(p)
        if t:
            body_paragraphs.append(t)
        if len(body_paragraphs) >= 200:
            break

    parts: list[str] = ["<!doctype html>", "<html><head>", '<meta charset="utf-8"/>']
    if title:
        parts.append(f"<title>{escape(title)}</title>")
    parts.append("</head><body>")
    if title:
        parts.append(f"<h1>{escape(title)}</h1>")
    if authors:
        parts.append(f"<p><strong>Authors:</strong> {escape(', '.join(authors))}</p>")
    if abstract_parts:
        parts.append("<h2>Abstract</h2>")
        for p in abstract_parts:
            parts.append(f"<p>{escape(p)}</p>")
    if body_paragraphs:
        parts.append("<h2>Body</h2>")
        for p in body_paragraphs:
            parts.append(f"<p>{escape(p)}</p>")

    parts.append("</body></html>")
    return "\n".join(parts)
