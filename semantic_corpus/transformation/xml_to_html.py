"""Convert JATS/PMC fulltext XML to HTML for browsing tables and figures."""

import html
from pathlib import Path
from typing import Any, Dict, List, Optional

from lxml import etree

from semantic_corpus.core.exceptions import CorpusError

_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
_PMC_IMAGE_BASE = (
    "https://www.ncbi.nlm.nih.gov/core/lw/2.0/html/tileshop_pmc/tileshop/inline"
)


def _local_name(tag: str) -> str:
    if isinstance(tag, str) and "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return str(tag)


def _text_content(element: etree._Element) -> str:
    return "".join(element.itertext()).strip()


def _children_html(element: etree._Element) -> str:
    """Serialize element text + children with tails interleaved in document order.

    Previous code appended all child tails after all children, which concatenated
    adjacent ``<sup>``/``<sub>`` runs (e.g. δ<sup>17</sup>Δ became wrong).
    """
    parts: List[str] = []
    if element.text:
        parts.append(html.escape(element.text))
    for child in element:
        parts.append(_inline_html(child))
        if child.tail:
            parts.append(html.escape(child.tail))
    return "".join(parts)


def _inline_html(element: etree._Element) -> str:
    """Render inline and block JATS elements to simple HTML."""
    name = _local_name(element.tag)
    if name in ("p", "sec", "abstract", "caption", "title", "label"):
        inner = _children_html(element)
        parent_name = (
            _local_name(element.getparent().tag)
            if element.getparent() is not None
            else ""
        )
        tag = "h2" if name == "title" and parent_name == "sec" else name
        if name == "title" and parent_name == "title-group":
            tag = "h1"
        if name == "abstract":
            tag = "div"
            return f'<{tag} class="abstract-block">{inner}</{tag}>'
        return f"<{tag}>{inner}</{tag}>"
    if name in ("bold", "italic", "underline", "sc"):
        tag_map = {"bold": "strong", "italic": "em", "underline": "u", "sc": "span"}
        tag = tag_map[name]
        cls = ' class="small-caps"' if name == "sc" else ""
        return f"<{tag}{cls}>{_children_html(element)}</{tag}>"
    if name == "sup":
        return f"<sup>{_children_html(element)}</sup>"
    if name == "sub":
        return f"<sub>{_children_html(element)}</sub>"
    if name == "xref":
        return html.escape(_text_content(element))
    if name == "email":
        addr = _text_content(element)
        return f'<a href="mailto:{html.escape(addr)}">{html.escape(addr)}</a>'
    if name == "ext-link":
        href = element.get(_XLINK_HREF) or element.get("href") or ""
        label = _text_content(element) or href
        if href:
            return (
                f'<a href="{html.escape(href)}" rel="noopener noreferrer">'
                f"{html.escape(label)}</a>"
            )
        return html.escape(label)
    if name == "list":
        items = element.findall(".//{*}list-item")
        lis = "".join(f"<li>{_inline_html(item)}</li>" for item in items)
        list_type = element.get("list-type", "bullet")
        tag = "ol" if list_type in ("order", "numbered") else "ul"
        return f"<{tag}>{lis}</{tag}>"
    if name == "table-wrap":
        return _render_table_wrap(element)
    if name == "fig":
        return _render_figure(element)
    if name == "table":
        return _render_table(element)
    if name == "graphic":
        return ""
    # Default: unwrap unknown tags but keep text order
    return _children_html(element)


def _find_pmcid(element: etree._Element) -> str:
    article = element
    while article is not None and _local_name(article.tag) != "article":
        article = article.getparent()
    if article is None:
        return ""
    for aid in article.findall(".//{*}article-id"):
        if aid.get("pub-id-type") == "pmcid" and aid.text:
            return aid.text.strip()
    return ""


def _pmc_image_url(pmcid: str, href: str) -> str:
    href = href.split("?")[0]
    pmcid = pmcid if pmcid.startswith("PMC") else f"PMC{pmcid}"
    return f"{_PMC_IMAGE_BASE}/{pmcid}/{href}"


def _render_figure(fig: etree._Element) -> str:
    fig_id = fig.get("id") or ""
    label_elem = fig.find(".//{*}label")
    caption_elem = fig.find(".//{*}caption")
    label = _text_content(label_elem) if label_elem is not None else ""
    caption = _inline_html(caption_elem) if caption_elem is not None else ""
    graphic = fig.find(".//{*}graphic")
    img_html = ""
    if graphic is not None:
        href = graphic.get(_XLINK_HREF) or graphic.get("href") or ""
        if href:
            pmcid = _find_pmcid(fig)
            src = _pmc_image_url(pmcid, href) if pmcid else html.escape(href)
            img_html = (
                f'<img src="{src}" alt="{html.escape(label or fig_id)}" '
                f'data-graphic-href="{html.escape(href)}" />'
            )
    id_attr = f' id="{html.escape(fig_id)}"' if fig_id else ""
    return (
        f'<figure class="pmc-figure"{id_attr} data-figure-id="{html.escape(fig_id)}">'
        f'<figcaption><span class="figure-label">{html.escape(label)}</span>{caption}</figcaption>'
        f"{img_html}</figure>"
    )


def _render_table_wrap(table_wrap: etree._Element) -> str:
    wrap_id = table_wrap.get("id") or ""
    label_elem = table_wrap.find(".//{*}label")
    caption_elem = table_wrap.find(".//{*}caption")
    label = _text_content(label_elem) if label_elem is not None else ""
    caption = _inline_html(caption_elem) if caption_elem is not None else ""
    table_elem = table_wrap.find(".//{*}table")
    table_html = _render_table(table_elem) if table_elem is not None else ""
    id_attr = f' id="{html.escape(wrap_id)}"' if wrap_id else ""
    return (
        f'<div class="pmc-table-wrap"{id_attr} data-table-id="{html.escape(wrap_id)}">'
        f'<div class="table-label">{html.escape(label)}</div>{caption}{table_html}</div>'
    )


def _render_table(table: etree._Element) -> str:
    rows: List[str] = []
    for child in table:
        name = _local_name(child.tag)
        if name == "thead":
            rows.append("<thead>" + _render_table_section(child) + "</thead>")
        elif name == "tbody":
            rows.append("<tbody>" + _render_table_section(child) + "</tbody>")
        elif name == "tr":
            rows.append(_render_table_row(child))
    return "<table>" + "".join(rows) + "</table>"


def _render_table_section(section: etree._Element) -> str:
    return "".join(_render_table_row(row) for row in section.findall("./{*}tr"))


def _render_table_row(row: etree._Element) -> str:
    cells: List[str] = []
    for cell in row:
        name = _local_name(cell.tag)
        if name not in ("td", "th"):
            continue
        colspan = cell.get("colspan")
        rowspan = cell.get("rowspan")
        attrs = ""
        if colspan:
            attrs += f' colspan="{html.escape(colspan)}"'
        if rowspan:
            attrs += f' rowspan="{html.escape(rowspan)}"'
        cells.append(f"<{name}{attrs}>{_inline_html(cell)}</{name}>")
    return f"<tr>{''.join(cells)}</tr>"


def _format_author_name(contrib: etree._Element) -> str:
    name_el = contrib.find("./{*}name")
    if name_el is None:
        collab = contrib.find("./{*}collab")
        return _text_content(collab) if collab is not None else ""
    given = name_el.findtext("./{*}given-names") or ""
    surname = name_el.findtext("./{*}surname") or ""
    full = f"{given} {surname}".strip()
    return full or _text_content(name_el)


def _author_aff_markers(contrib: etree._Element) -> str:
    marks: List[str] = []
    for xref in contrib.findall("./{*}xref"):
        ref_type = xref.get("ref-type") or ""
        if ref_type in ("aff", "corresp", "author-notes"):
            marks.append(_text_content(xref) or xref.get("rid") or "")
    marks = [m for m in marks if m]
    if not marks:
        return ""
    return "<sup>" + ",".join(html.escape(m) for m in marks) + "</sup>"


def _render_front_matter(root: etree._Element) -> str:
    """Authors, affiliations, journal, ids, dates from ``<front>``."""
    front = root.find(".//{*}front")
    if front is None:
        return ""

    parts: List[str] = []

    journal = front.findtext(".//{*}journal-title") or ""
    if journal:
        parts.append(
            f'<p class="journal"><em>{html.escape(journal.strip())}</em></p>'
        )

    meta_bits: List[str] = []
    for pub_id_type, label in (
        ("doi", "DOI"),
        ("pmid", "PMID"),
        ("pmcid", "PMCID"),
    ):
        for aid in front.findall(".//{*}article-id"):
            if aid.get("pub-id-type") == pub_id_type and (aid.text or "").strip():
                meta_bits.append(
                    f"{label}: {html.escape(aid.text.strip())}"
                )
                break
    pub_date = front.find(".//{*}pub-date")
    if pub_date is not None:
        y = pub_date.findtext("./{*}year") or ""
        m = pub_date.findtext("./{*}month") or ""
        d = pub_date.findtext("./{*}day") or ""
        date_s = "-".join(p for p in (y, m.zfill(2) if m else "", d.zfill(2) if d else "") if p)
        if date_s:
            meta_bits.append(f"Published: {html.escape(date_s)}")
    if meta_bits:
        parts.append(f'<p class="meta ids">{" | ".join(meta_bits)}</p>')

    authors: List[str] = []
    for group in front.findall(".//{*}contrib-group"):
        for contrib in group.findall("./{*}contrib"):
            # Skip non-author contribs when typed
            ctype = (contrib.get("contrib-type") or "author").lower()
            if ctype not in ("author", ""):
                continue
            name = _format_author_name(contrib)
            if not name:
                continue
            authors.append(
                f'<span class="author">{html.escape(name)}'
                f"{_author_aff_markers(contrib)}</span>"
            )
    if authors:
        parts.append(
            '<p class="authors">' + ", ".join(authors) + "</p>"
        )

    affs: List[str] = []
    for aff in front.findall(".//{*}aff"):
        aff_id = aff.get("id") or ""
        label_el = aff.find("./{*}label")
        label = _inline_html(label_el) if label_el is not None else ""
        # Clone-ish: text without re-emitting label twice
        body = _text_content(aff)
        if label_el is not None:
            label_plain = _text_content(label_el)
            if body.startswith(label_plain):
                body = body[len(label_plain) :].lstrip()
        affs.append(
            f'<li id="{html.escape(aff_id)}">{label} {html.escape(body)}</li>'
        )
    if affs:
        parts.append('<ol class="affiliations">' + "".join(affs) + "</ol>")

    notes = front.find(".//{*}author-notes")
    if notes is not None:
        note_bits: List[str] = []
        for fn in notes.findall("./{*}fn"):
            note_bits.append(f"<li>{_inline_html(fn)}</li>")
        if note_bits:
            parts.append(
                '<ul class="author-notes">' + "".join(note_bits) + "</ul>"
            )

    if not parts:
        return ""
    return '<section class="front-matter">' + "".join(parts) + "</section>"


def convert_xml_to_html(
    xml_path: Path,
    html_path: Path,
    *,
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    """Convert a PMC/JATS XML file to HTML preserving tables and figures."""
    xml_path = Path(xml_path)
    html_path = Path(html_path)
    if not xml_path.is_file():
        raise CorpusError(f"XML file not found: {xml_path}")

    try:
        tree = etree.parse(str(xml_path))
    except etree.XMLSyntaxError as exc:
        raise CorpusError(f"Invalid XML: {xml_path}: {exc}") from exc

    root = tree.getroot()
    title_elem = root.find(".//{*}article-title")
    title = (metadata or {}).get("title") or (
        _text_content(title_elem) if title_elem is not None else xml_path.stem
    )

    # Prefer the main abstract (skip teaser / graphical when typed)
    abstract_html = ""
    for abstract_elem in root.findall(".//{*}abstract"):
        atype = (abstract_elem.get("abstract-type") or "").lower()
        if atype in ("teaser", "graphical", "summary"):
            continue
        abstract_html = _inline_html(abstract_elem)
        break
    if not abstract_html:
        abstract_elem = root.find(".//{*}abstract")
        if abstract_elem is not None:
            abstract_html = _inline_html(abstract_elem)

    front_html = _render_front_matter(root)

    body_parts: List[str] = []
    body = root.find(".//{*}body")
    if body is not None:
        for sec in body.findall("./{*}sec"):
            body_parts.append(_inline_html(sec))
        if not body_parts:
            body_parts.append(_inline_html(body))

    figure_count = len(root.findall(".//{*}fig"))
    table_count = len(root.findall(".//{*}table-wrap"))

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{html.escape(title)}</title>
<style>
body {{ font-family: Georgia, serif; max-width: 900px; margin: 2rem auto; line-height: 1.5; }}
h1 {{ font-size: 1.6rem; }}
.front-matter {{ margin: 1rem 0 1.5rem; }}
.authors {{ margin: 0.5rem 0; }}
.affiliations {{ font-size: 0.9rem; color: #444; }}
.author-notes {{ font-size: 0.85rem; color: #555; }}
.pmc-figure, .pmc-table-wrap {{ margin: 1.5rem 0; border: 1px solid #ddd; padding: 1rem; }}
.pmc-figure img, .pmc-table-wrap img {{ max-width: 100%; height: auto; }}
.table-label, .figure-label {{ font-weight: bold; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }}
.meta {{ color: #555; font-size: 0.9rem; }}
.abstract-block {{ margin: 1rem 0; }}
</style>
</head>
<body>
<header>
<h1>{html.escape(title)}</h1>
<p class="meta">Figures: {figure_count} | Tables: {table_count} | Source: {html.escape(xml_path.name)}</p>
</header>
{front_html}
<section class="abstract">{abstract_html}</section>
<main>{"".join(body_parts)}</main>
</body>
</html>
"""
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(doc, encoding="utf-8")
    return html_path


def convert_corpus_xml_to_html(corpus_dir: Path) -> Dict[str, Path]:
    """Convert all XML files in a BAGIT corpus to HTML under data/documents/html/."""
    corpus_dir = Path(corpus_dir)
    xml_dir = Path(corpus_dir, "data", "documents", "xml")
    html_dir = Path(corpus_dir, "data", "documents", "html")
    if not xml_dir.is_dir():
        raise CorpusError(f"Corpus XML directory not found: {xml_dir}")

    written: Dict[str, Path] = {}
    for xml_path in sorted(xml_dir.glob("*.xml")):
        paper_id = xml_path.stem
        html_path = Path(html_dir, f"{paper_id}.html")
        convert_xml_to_html(xml_path, html_path)
        written[paper_id] = html_path
    return written
