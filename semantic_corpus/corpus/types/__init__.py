"""Shared corpus type slugs, field names, and light I/O helpers.

Owned by ``corpus/`` for all submodules (``phrases_kg``, chatbot, encyclopedia, …).
See ``docs/indexed_text.md`` and ``types_io_storage.md``.
"""

from semantic_corpus.corpus.types.indexed_text import (
    INDEXED_JSON_GLOB,
    INDEXED_JSON_SUFFIX,
    BlockFields,
    BlockKind,
    IndexedDocType,
    IndexedTextFields,
    MetadataFields,
    SourceFields,
    blocks_of_kinds,
    iter_blocks,
    load_indexed_text,
    load_indexed_texts,
    validate_indexed_text,
)

__all__ = [
    "INDEXED_JSON_GLOB",
    "INDEXED_JSON_SUFFIX",
    "BlockFields",
    "BlockKind",
    "IndexedDocType",
    "IndexedTextFields",
    "MetadataFields",
    "SourceFields",
    "blocks_of_kinds",
    "iter_blocks",
    "load_indexed_text",
    "load_indexed_texts",
    "validate_indexed_text",
]
