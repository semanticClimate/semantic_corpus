"""Sectioner (partial): mint heuristic text_block ids on HTML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Union

from bs4 import BeautifulSoup, Tag

from semantic_corpus.corpus.types import BlockKind, IndexedDocType, IndexedTextFields

# Elements treated as text_block candidates (see definitions_text_block.md)
_BLOCK_TAGS = {
    "p": BlockKind.PARAGRAPH.value,
    "figcaption": BlockKind.FIGCAPTION.value,
    "caption": BlockKind.TABLECAPTION.value,
    "li": BlockKind.LISTITEM.value,
    "h1": BlockKind.HEADING.value,
    "h2": BlockKind.HEADING.value,
    "h3": BlockKind.HEADING.value,
    "h4": BlockKind.HEADING.value,
    "h5": BlockKind.HEADING.value,
    "h6": BlockKind.HEADING.value,
    "blockquote": BlockKind.BLOCKQUOTE.value,
    "dd": BlockKind.DEFINITION.value,
}

_KIND_PREFIX = {
    BlockKind.PARAGRAPH.value: "p",
    BlockKind.FIGCAPTION.value: "figcaption",
    BlockKind.TABLECAPTION.value: "tablecaption",
    BlockKind.LISTITEM.value: "li",
    BlockKind.HEADING.value: "h",
    BlockKind.BLOCKQUOTE.value: "bq",
    BlockKind.DEFINITION.value: "dd",
}


def mint_text_block_ids_in_html(
    html: str,
    *,
    paper_id: str = "doc",
    id_scheme: str = "v1",
) -> Dict[str, Any]:
    """Add stable ids to block elements that lack them; return semantic payload.

    Args:
        html: HTML string (may be messy; should be Unicode).
        paper_id: Document id prefix for block ids.
        id_scheme: Recorded in output for skip-satisfied stamps.

    Returns:
        Dict with keys: ``paper_id``, ``html``, ``blocks``, ``id_scheme``.
    """
    soup = BeautifulSoup(html, "lxml")
    counters: Dict[str, int] = {}
    blocks: List[Dict[str, Any]] = []
    order = 0

    for tag in soup.find_all(list(_BLOCK_TAGS.keys())):
        if not isinstance(tag, Tag):
            continue
        kind = _BLOCK_TAGS[tag.name]
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        counters[kind] = counters.get(kind, 0) + 1
        prefix = _KIND_PREFIX.get(kind, kind)
        local = f"{prefix}-{counters[kind]:03d}"
        block_id = tag.get("id") or f"{paper_id}#{local}"
        if not tag.get("id"):
            tag["id"] = block_id
        tag["data-tb-kind"] = kind
        order += 1
        blocks.append(
            {
                "id": block_id,
                "kind": kind,
                "text": text,
                "order": order,
            }
        )

    return {
        IndexedTextFields.TYPE: IndexedDocType.INDEXED_TEXT.value,
        IndexedTextFields.PAPER_ID: paper_id,
        IndexedTextFields.HTML: str(soup),
        IndexedTextFields.BLOCKS: blocks,
        IndexedTextFields.ID_SCHEME: id_scheme,
        IndexedTextFields.METADATA: {},
    }


def html_file_to_semantic(
    path: Union[Path, str],
    *,
    paper_id: str = "doc",
    id_scheme: str = "v1",
) -> Dict[str, Any]:
    """Load an HTML file and mint text_block ids."""
    html = Path(path).read_text(encoding="utf-8")
    return mint_text_block_ids_in_html(html, paper_id=paper_id, id_scheme=id_scheme)
