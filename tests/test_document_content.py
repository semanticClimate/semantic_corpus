"""Tests: never save error stubs as XML/PDF; never overwrite good files."""

from __future__ import annotations

from pathlib import Path

import pytest
import requests

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.repositories._ids import (
    existing_document_paths,
    paper_documents_present,
)
from semantic_corpus.repositories.document_content import (
    is_valid_document_file,
    looks_like_fulltext_xml,
    looks_like_pdf,
    safe_write_document,
)
from semantic_corpus.repositories.europe_pmc import EuropePMCRepository

_ERROR_JSON = (
    b'{"timestamp":"2026-11-08T09:14:32.370+00:00","status":500,'
    b'"error":"Internal Server Error",'
    b'"path":"/europepmc/webservices/rest/PMC1/fullTextXML"}'
)
_GOOD_XML = b'<?xml version="1.0"?><article><body>ok</body></article>'
_GOOD_PDF = b"%PDF-1.4\n" + (b"0" * 80)


def test_looks_like_rejects_error_json():
    assert looks_like_fulltext_xml(_ERROR_JSON) is False
    assert looks_like_pdf(_ERROR_JSON) is False
    assert looks_like_pdf(_GOOD_PDF) is True
    assert looks_like_fulltext_xml(_GOOD_XML) is True


def test_safe_write_refuses_error_stub(tmp_path: Path):
    dest = tmp_path / "PMC1.xml"
    assert safe_write_document(dest, _ERROR_JSON, fmt="xml") is False
    assert not dest.exists()


def test_safe_write_does_not_overwrite_good_xml_with_error(tmp_path: Path):
    dest = tmp_path / "PMC1.xml"
    dest.write_bytes(_GOOD_XML)
    assert safe_write_document(dest, _ERROR_JSON, fmt="xml") is True
    assert dest.read_bytes() == _GOOD_XML


def test_safe_write_does_not_overwrite_good_pdf_with_html(tmp_path: Path):
    dest = tmp_path / "PMC1.pdf"
    dest.write_bytes(_GOOD_PDF)
    assert safe_write_document(dest, b"<html>403</html>", fmt="pdf") is True
    assert dest.read_bytes() == _GOOD_PDF


def test_safe_write_replaces_error_stub_with_good_xml(tmp_path: Path):
    dest = tmp_path / "PMC1.xml"
    dest.write_bytes(_ERROR_JSON)
    assert is_valid_document_file(dest, "xml") is False
    assert safe_write_document(dest, _GOOD_XML, fmt="xml") is True
    assert dest.read_bytes() == _GOOD_XML


def test_existing_paths_ignore_error_stubs(tmp_path: Path):
    stub = tmp_path / "documents" / "PMC1.xml"
    stub.parent.mkdir(parents=True)
    stub.write_bytes(_ERROR_JSON)
    assert existing_document_paths(tmp_path, "PMC1", ["xml"]) == {}
    assert paper_documents_present(tmp_path, "PMC1", ["xml"]) is False

    stub.write_bytes(_GOOD_XML)
    found = existing_document_paths(tmp_path, "PMC1", ["xml"])
    assert "xml" in found
    assert paper_documents_present(tmp_path, "PMC1", ["xml"]) is True


def test_download_does_not_create_files_on_500(tmp_path: Path, monkeypatch):
    class FakeResponse:
        status_code = 500
        content = _ERROR_JSON
        text = _ERROR_JSON.decode()

        def raise_for_status(self) -> None:
            err = requests.HTTPError("500 Server Error")
            err.response = self
            raise err

    monkeypatch.setattr(
        "semantic_corpus.repositories.europe_pmc.requests.get",
        lambda *a, **k: FakeResponse(),
    )
    monkeypatch.setattr(
        EuropePMCRepository,
        "_download_pdf",
        lambda self, *a, **k: None,
    )
    repo = EuropePMCRepository()
    with pytest.raises(RepositoryError, match="HTTP 500"):
        repo.download_paper("PMC1", tmp_path, formats=["xml"])
    assert list(tmp_path.rglob("*.xml")) == []
    assert list(tmp_path.rglob("*.pdf")) == []


def test_download_preserves_existing_good_xml(tmp_path: Path, monkeypatch):
    docs = tmp_path / "documents"
    docs.mkdir()
    good = docs / "PMC1.xml"
    good.write_bytes(_GOOD_XML)

    monkeypatch.setattr(
        EuropePMCRepository,
        "_download_pdf",
        lambda self, *a, **k: None,
    )
    # Existing good file → skip network path via existing_document_paths
    repo = EuropePMCRepository()
    result = repo.download_paper("PMC1", tmp_path, formats=["xml"])
    assert result.get("success") is True
    assert good.read_bytes() == _GOOD_XML


def test_download_purges_stub_and_does_not_rewrite_error(tmp_path: Path, monkeypatch):
    stub = tmp_path / "documents" / "PMC1.xml"
    stub.parent.mkdir(parents=True)
    stub.write_bytes(_ERROR_JSON)

    class FakeResponse:
        status_code = 200
        content = _ERROR_JSON
        text = _ERROR_JSON.decode()

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        "semantic_corpus.repositories.europe_pmc.requests.get",
        lambda *a, **k: FakeResponse(),
    )
    monkeypatch.setattr(
        EuropePMCRepository,
        "_download_pdf",
        lambda self, *a, **k: None,
    )
    repo = EuropePMCRepository()
    with pytest.raises(RepositoryError, match="HTTP 500"):
        repo.download_paper("PMC1", tmp_path, formats=["xml"])
    assert not stub.exists()
    assert list(tmp_path.rglob("*.xml")) == []
