"""Tests for update_bagit_formats (BAGIT PDF refresh)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from semantic_corpus.cluster_review.step0 import create_corpus_from_query
from semantic_corpus.cluster_review.update_corpus import (
    is_valid_pdf,
    pdf_path_for_paper,
    pmcid_from_paper_id,
    update_bagit_formats,
)
from semantic_corpus.core.exceptions import CorpusError


def _fake_search_download(
    *,
    query_string: str,
    repository: str,
    limit: int,
    output_dir: Path,
    formats,
    start_date: str = None,
    end_date: str = None,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for i in range(limit):
        pmcid = f"PMC6{i:06d}"
        Path(output_dir, f"{pmcid}.xml").write_text(
            f"<article><title>Update paper {i}</title></article>",
            encoding="utf-8",
        )
        results.append(
            {
                "pmcid": pmcid,
                "title": f"Update paper {i}",
                "abstract": f"Abstract {i}",
                "authors": [{"fullName": "Tester"}],
                "publication_date": "2024-06-01",
            }
        )
    return results, len(results)


def _minimal_pdf_bytes(size: int = 12_000) -> bytes:
    # Valid header + padding so size clears MIN_PDF_BYTES
    body = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    if len(body) < size:
        body = body + (b"0" * (size - len(body)))
    return body


@pytest.fixture
def mini_bagit(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        "semantic_corpus.cluster_review.step0.run_repository_search",
        _fake_search_download,
    )
    corpus_dir = Path(temp_dir, "corpora", "update_mini")
    create_corpus_from_query(
        query_string="test",
        query_name="update_mini",
        query_dir=Path(temp_dir, "queries", "update_mini"),
        limit=2,
        formats=["xml"],
        corpus_dir=corpus_dir,
        create_bagit=True,
    )
    return corpus_dir


class TestHelpers:
    def test_pmcid_from_paper_id(self) -> None:
        assert pmcid_from_paper_id("europe_pmc_PMC1234567") == "PMC1234567"
        assert pmcid_from_paper_id("PMC999") == "PMC999"
        assert pmcid_from_paper_id("nope") is None

    def test_is_valid_pdf_rejects_html_stub(self, temp_dir: Path) -> None:
        path = Path(temp_dir, "bad.pdf")
        path.write_text(
            "<html><body><h1>403 Forbidden</h1></body></html>\n",
            encoding="utf-8",
        )
        assert is_valid_pdf(path) is False

    def test_is_valid_pdf_accepts_realish(self, temp_dir: Path) -> None:
        path = Path(temp_dir, "ok.pdf")
        path.write_bytes(_minimal_pdf_bytes())
        assert is_valid_pdf(path) is True


class TestUpdateBagitFormats:
    def test_downloads_missing_pdfs(
        self, mini_bagit: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fake_download(pmcid: str, dest: Path) -> None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(_minimal_pdf_bytes())

        monkeypatch.setattr(
            "semantic_corpus.cluster_review.update_corpus._download_europe_pmc_pdf",
            _fake_download,
        )
        summary = update_bagit_formats(mini_bagit, formats=["pdf"])
        assert summary["downloaded"] == 2
        assert summary["skipped"] == 0
        assert summary["failed"] == 0
        for paper in summary["papers"]:
            path = Path(paper["path"])
            assert is_valid_pdf(path)

        # Second run skips
        again = update_bagit_formats(mini_bagit, formats=["pdf"])
        assert again["downloaded"] == 0
        assert again["skipped"] == 2

    def test_replaces_invalid_html_pdf(
        self, mini_bagit: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from semantic_corpus.cluster_review.step1 import resolve_bagit_root

        bag_root = resolve_bagit_root(mini_bagit)
        paper_id = "europe_pmc_PMC6000000"
        dest = pdf_path_for_paper(bag_root, paper_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            "<html><body><h1>403 Forbidden</h1></body></html>\n",
            encoding="utf-8",
        )
        assert is_valid_pdf(dest) is False

        def _fake_download(pmcid: str, dest_path: Path) -> None:
            dest_path.write_bytes(_minimal_pdf_bytes())

        monkeypatch.setattr(
            "semantic_corpus.cluster_review.update_corpus._download_europe_pmc_pdf",
            _fake_download,
        )
        summary = update_bagit_formats(
            mini_bagit, formats=["pdf"], paper_ids=[paper_id]
        )
        assert summary["downloaded"] == 1
        assert summary["replaced_invalid"] >= 1
        assert is_valid_pdf(dest)

    def test_records_failure(
        self, mini_bagit: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _boom(pmcid: str, dest: Path) -> None:
            raise CorpusError(f"no pdf for {pmcid}")

        monkeypatch.setattr(
            "semantic_corpus.cluster_review.update_corpus._download_europe_pmc_pdf",
            _boom,
        )
        summary = update_bagit_formats(mini_bagit, formats=["pdf"])
        assert summary["failed"] == 2
        assert summary["downloaded"] == 0
        assert all(p["status"] == "failed" for p in summary["papers"])

    def test_refreshes_review_has_pdf(
        self, mini_bagit: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from semantic_corpus.cluster_review.step1 import load_bagit_corpus

        # Step 0 bag may have no review table yet — build one via Step 1
        loaded = load_bagit_corpus(mini_bagit, write_review_if_missing=True)
        review_path = Path(loaded["review_paths"]["json"])
        assert review_path.is_file()
        rows = json.loads(review_path.read_text(encoding="utf-8"))
        for row in rows:
            row["has_pdf"] = False
        review_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

        def _fake(pmcid: str, dest: Path) -> None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(_minimal_pdf_bytes())

        monkeypatch.setattr(
            "semantic_corpus.cluster_review.update_corpus._download_europe_pmc_pdf",
            _fake,
        )
        summary = update_bagit_formats(mini_bagit, formats=["pdf"])
        assert summary["review_table"]
        updated = json.loads(review_path.read_text(encoding="utf-8"))
        assert all(row.get("has_pdf") for row in updated)

    def test_rejects_unsupported_format(self, mini_bagit: Path) -> None:
        with pytest.raises(CorpusError, match="Unsupported update formats"):
            update_bagit_formats(mini_bagit, formats=["xml"])
