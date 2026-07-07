"""Tests for document path resolution."""

from pathlib import Path

from semantic_corpus.corpus_review.text_preview import resolve_document_paths


def test_resolve_html_by_paper_id_in_query_dir(tmp_path: Path) -> None:
    query_dir = tmp_path / "query"
    query_dir.mkdir()
    row = {
        "pmcid": "PMC1",
        "paper_id": "europe_pmc_PMC1",
    }
    (query_dir / "PMC1.pdf").write_bytes(b"%PDF")
    (query_dir / "europe_pmc_PMC1.html").write_text("<html><body>paper</body></html>")

    paths = resolve_document_paths(row, query_dir=query_dir)
    assert paths["pdf_path"] == query_dir / "PMC1.pdf"
    assert paths["html_path"] == query_dir / "europe_pmc_PMC1.html"


def test_resolve_html_in_nested_corpus_data_dir(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "corpus"
    nested = corpus_dir / "data" / "data" / "documents" / "html"
    nested.mkdir(parents=True)
    html_file = nested / "europe_pmc_PMC99.html"
    html_file.write_text("<html><body>nested</body></html>", encoding="utf-8")

    row = {"pmcid": "PMC99", "paper_id": "europe_pmc_PMC99"}
    paths = resolve_document_paths(row, corpus_dir=corpus_dir)
    assert paths["html_path"] == html_file
