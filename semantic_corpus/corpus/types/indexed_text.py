"""Generic ``indexed_text`` types and loaders (shared by all downstream modules).

Closed vocabularies use ``str, Enum`` for Python 3.8+. Prefer ``enum.StrEnum``
when the project requires Python 3.11+.

Normative prose: ``semantic_corpus/corpus/docs/indexed_text.md``.
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Union


INDEXED_JSON_SUFFIX = ".indexed.json"
INDEXED_JSON_GLOB = f"*{INDEXED_JSON_SUFFIX}"


class IndexedDocType(str, Enum):
    """Top-level ``type`` discriminator for the consumer intermediate."""

    INDEXED_TEXT = "indexed_text"


class BlockKind(str, Enum):
    """``text_block.kind`` slugs (corpus vocabulary; extend as kinds land).

    Keep in sync with ``definitions_text_block.md``.
    """

    PARAGRAPH = "paragraph"
    FIGCAPTION = "figcaption"
    TABLECAPTION = "tablecaption"
    LISTITEM = "listitem"
    HEADING = "heading"
    BLOCKQUOTE = "blockquote"
    FOOTNOTE = "footnote"
    TITLE = "title"
    ABSTRACT_BLOCK = "abstract_block"
    BOXED_TEXT = "boxed_text"
    ALT_TEXT = "alt_text"
    DEFINITION = "definition"
    PREFORMATTED = "preformatted"


class IndexedTextFields:
    """Canonical JSON keys on an ``indexed_text`` object (open set)."""

    TYPE = "type"
    PAPER_ID = "paper_id"
    ID_SCHEME = "id_scheme"
    BLOCKS = "blocks"
    METADATA = "metadata"
    SOURCE = "source"
    SECTIONS = "sections"
    HTML = "html"
    WARNINGS = "warnings"


class BlockFields:
    """Canonical keys on each ``text_block`` entry."""

    ID = "id"
    KIND = "kind"
    TEXT = "text"
    ORDER = "order"
    PARENT_ID = "parent_id"


class MetadataFields:
    """Common ``metadata`` keys (bibliographic / citation)."""

    TITLE = "title"
    AUTHORS = "authors"
    PUBLICATION_DATE = "publication_date"
    JOURNAL = "journal"
    PUBLISHER = "publisher"
    DOI = "doi"
    PMCID = "pmcid"
    PMID = "pmid"
    LICENSE = "license"
    LANGUAGE = "language"
    ABSTRACT = "abstract"
    CITATION_LABEL = "citation_label"
    REPOSITORY = "repository"
    LANDING_URL = "landing_url"
    CHAPTER = "chapter"
    REPORT = "report"


class SourceFields:
    """Common ``source`` provenance keys."""

    EXTRACTOR = "extractor"
    CONTENT_FORMAT = "content_format"
    CONTENT_PATH = "content_path"
    METADATA_PATH = "metadata_path"
    URI = "uri"
    RETRIEVED_AT = "retrieved_at"


def validate_indexed_text(doc: Dict[str, Any], *, path: Optional[Path] = None) -> None:
    """Raise ``ValueError`` if required ``indexed_text`` fields are missing."""
    where = f"{path}: " if path is not None else ""
    if doc.get(IndexedTextFields.TYPE) != IndexedDocType.INDEXED_TEXT.value:
        raise ValueError(
            f"{where}type must be {IndexedDocType.INDEXED_TEXT.value!r}"
        )
    if not doc.get(IndexedTextFields.PAPER_ID):
        raise ValueError(f"{where}missing {IndexedTextFields.PAPER_ID}")
    blocks = doc.get(IndexedTextFields.BLOCKS)
    if not isinstance(blocks, list):
        raise ValueError(f"{where}missing {IndexedTextFields.BLOCKS} list")
    if IndexedTextFields.METADATA not in doc:
        raise ValueError(f"{where}missing {IndexedTextFields.METADATA}")
    if not isinstance(doc[IndexedTextFields.METADATA], dict):
        raise ValueError(f"{where}{IndexedTextFields.METADATA} must be an object")


def load_indexed_text(path: Union[Path, str]) -> Dict[str, Any]:
    """Load and validate one ``*.indexed.json`` (or any JSON ``indexed_text``)."""
    p = Path(path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError(f"{p}: expected a JSON object")
    validate_indexed_text(doc, path=p)
    return doc


def load_indexed_texts(paths: Sequence[Union[Path, str]]) -> List[Dict[str, Any]]:
    """Load many ``indexed_text`` documents in given order."""
    return [load_indexed_text(p) for p in paths]


def iter_blocks(
    docs: Iterable[Dict[str, Any]],
    *,
    kinds: Optional[Sequence[Union[str, BlockKind]]] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield normalised block dicts, optionally filtered by ``kind``.

    Each yield includes ``id``, ``kind``, ``text``, ``order?``, ``parent_id?``,
    plus ``paper_id`` and ``citation_label`` from the parent document.
    """
    kind_set = None
    if kinds is not None:
        kind_set = {
            k.value if isinstance(k, BlockKind) else str(k) for k in kinds
        }

    for doc in docs:
        paper_id = doc[IndexedTextFields.PAPER_ID]
        meta = doc.get(IndexedTextFields.METADATA) or {}
        citation = meta.get(MetadataFields.CITATION_LABEL, paper_id)
        for block in doc[IndexedTextFields.BLOCKS]:
            if not isinstance(block, dict):
                continue
            kind = block.get(BlockFields.KIND)
            if kind_set is not None and kind not in kind_set:
                continue
            text = block.get(BlockFields.TEXT)
            if not text:
                continue
            item = {
                BlockFields.ID: block[BlockFields.ID],
                BlockFields.KIND: kind,
                BlockFields.TEXT: text,
                IndexedTextFields.PAPER_ID: paper_id,
                MetadataFields.CITATION_LABEL: citation,
            }
            if BlockFields.ORDER in block:
                item[BlockFields.ORDER] = block[BlockFields.ORDER]
            if BlockFields.PARENT_ID in block:
                item[BlockFields.PARENT_ID] = block[BlockFields.PARENT_ID]
            yield item


def blocks_of_kinds(
    docs: Iterable[Dict[str, Any]],
    kinds: Sequence[Union[str, BlockKind]],
) -> List[Dict[str, Any]]:
    """Materialise ``iter_blocks`` filtered by ``kinds``."""
    return list(iter_blocks(docs, kinds=kinds))
