"""Convert JATS/PMC fulltext XML to HTML for browsing tables and figures."""

import html
from pathlib import Path
from typing import Any, Dict, List, Optional

from lxml import etree

from semantic_corpus.core.exceptions import CorpusError

_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
_PMC_IMAGE_BASE = "https://www.ncbi.nlm.nih.gov/core/lw/2.0/html/tileshop_pmc/tileshop/inline"


def _local_name(tag: str) -> str:
    if isinstance(tag, str) and "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return str(tag)


def _text_content(element: etree._Element) -> str:
    return "".join(element.itertext()).strip()


def _inline_html(element: etree._Element) -> str:
    """Render inline and block JATS elements to simple HTML."""
    name = _local_name(element.tag)
    if name in ("p", "sec", "abstract", "caption", "title", "label"):
        inner = "".join(_inline_html(child) for child in element)
        if element.text:
            inner = html.escape(element.text) + inner
        for child in element:
            if child.tail:
                inner += html.escape(child.tail)
        parent_name = _local_name(element.getparent().tag) if element.getparent() is not None else ""
        tag = "h2" if name == "title" and parent_name == "sec" else name
        if name == "title" and parent_name == "title-group":
            tag = "h1"
        return f"<{tag}>{inner}</{tag}>"
    if name in ("bold", "italic", "underline", "sc"):
        tag_map = {"bold": "strong", "italic": "em", "underline": "u", "sc": "span"}
        tag = tag_map[name]
        inner = "".join(_inline_html(child) for child in element)
        if element.text:
            inner = html.escape(element.text) + inner
        for child in element:
            if child.tail:
                inner += html.escape(child.tail)
        cls = ' class="small-caps"' if name == "sc" else ""
        return f"<{tag}{cls}>{inner}</{tag}>"
    if name == "sup":
        inner = "".join(_inline_html(child) for child in element)
        if element.text:
            inner = html.escape(element.text) + inner
        return f"<sup>{inner}</sup>"
    if name == "sub":
        inner = "".join(_inline_html(child) for child in element)
        if element.text:
            inner = html.escape(element.text) + inner
        return f"<sub>{inner}</sub>"
    if name == "xref":
        return html.escape(_text_content(element))
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
    inner = "".join(_inline_html(child) for child in element)
    if element.text:
        inner = html.escape(element.text) + inner
    for child in element:
        if child.tail:
            inner += html.escape(child.tail)
    return inner


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

    abstract_elem = root.find(".//{*}abstract")
    abstract_html = _inline_html(abstract_elem) if abstract_elem is not None else ""

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
.pmc-figure, .pmc-table-wrap {{ margin: 1.5rem 0; border: 1px solid #ddd; padding: 1rem; }}
.pmc-figure img, .pmc-table-wrap img {{ max-width: 100%; height: auto; }}
.table-label, .figure-label {{ font-weight: bold; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.6rem; text-align: left; }}
.meta {{ color: #555; font-size: 0.9rem; }}
</style>
</head>
<body>
<header>
<h1>{html.escape(title)}</h1>
<p class="meta">Figures: {figure_count} | Tables: {table_count} | Source: {html.escape(xml_path.name)}</p>
</header>
<section class="abstract">{abstract_html}</section>
<main>{''.join(body_parts)}</main>
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
