"""Skip download when documents already exist under documents/ layouts."""

from __future__ import annotations

from pathlib import Path

from semantic_corpus.repositories._ids import (
    existing_document_paths,
    paper_documents_present,
)


def test_detects_documents_subdir(tmp_path: Path) -> None:
    docs = Path(tmp_path, "documents")
    docs.mkdir()
    xml = Path(docs, "PMC123.xml")
    xml.write_text("<article/>", encoding="utf-8")
    assert paper_documents_present(tmp_path, "PMC123", ["xml"])
    assert existing_document_paths(tmp_path, "PMC123", ["xml"])["xml"] == xml


def test_detects_bagit_layout(tmp_path: Path) -> None:
    xml = Path(tmp_path, "data", "documents", "xml", "europe_pmc_PMC999.xml")
    xml.parent.mkdir(parents=True)
    xml.write_text("<article/>", encoding="utf-8")
    assert paper_documents_present(tmp_path, "PMC999", ["xml"])
    assert paper_documents_present(tmp_path, "europe_pmc_PMC999", ["xml"])


def test_missing_format_not_present(tmp_path: Path) -> None:
    Path(tmp_path, "documents").mkdir()
    Path(tmp_path, "documents", "PMC1.xml").write_text("<a/>", encoding="utf-8")
    assert paper_documents_present(tmp_path, "PMC1", ["xml"])
    assert not paper_documents_present(tmp_path, "PMC1", ["xml", "pdf"])
