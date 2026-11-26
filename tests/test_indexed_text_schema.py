"""Validate sample indexed_text fixtures against the JSON Schema when available."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "semantic_corpus" / "corpus" / "schemas" / "indexed_text.schema.json"
IPCC = ROOT / "examples" / "phrases_kg_ipcc_captions" / "data"


def test_schema_file_is_valid_json() -> None:
    assert SCHEMA.is_file()
    data = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert data.get("title") == "indexed_text"
    assert data["properties"]["type"]["const"] == "indexed_text"


def test_ipcc_samples_match_schema() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Validator = jsonschema.Draft202012Validator
    validator = Validator(schema)
    paths = sorted(IPCC.glob("*.indexed.json"))
    assert paths
    for path in paths:
        doc = json.loads(path.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(doc), key=lambda e: e.path)
        assert not errors, f"{path}: " + "; ".join(e.message for e in errors)
