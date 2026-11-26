"""Tests for shared corpus.types.indexed_text component."""

from __future__ import annotations

from pathlib import Path

import pytest

from semantic_corpus.corpus.types import (
    BlockKind,
    IndexedDocType,
    IndexedTextFields,
    blocks_of_kinds,
    load_indexed_text,
    load_indexed_texts,
    validate_indexed_text,
)

IPCC_DATA = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "phrases_kg_ipcc_captions"
    / "data"
)


def test_load_ipcc_indexed_texts() -> None:
    paths = sorted(IPCC_DATA.glob("*.indexed.json"))
    docs = load_indexed_texts(paths)
    assert len(docs) == 2
    for doc in docs:
        assert doc[IndexedTextFields.TYPE] == IndexedDocType.INDEXED_TEXT.value
        validate_indexed_text(doc)


def test_blocks_of_kinds_figcaption() -> None:
    docs = load_indexed_texts(sorted(IPCC_DATA.glob("*.indexed.json")))
    caps = blocks_of_kinds(docs, (BlockKind.FIGCAPTION,))
    assert len(caps) >= 6
    assert all(c["kind"] == BlockKind.FIGCAPTION.value for c in caps)


def test_validate_rejects_wrong_type(tmp_path: Path) -> None:
    bad = tmp_path / "x.indexed.json"
    bad.write_text(
        '{"type":"nope","paper_id":"x","blocks":[],"metadata":{}}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="indexed_text"):
        load_indexed_text(bad)
