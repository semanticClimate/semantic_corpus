"""Tests for importing local PDF directories into a corpus."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.ingestion.local_pdf_ingester import ingest_local_pdf_directory


def _write_pdf(path: Path, body: bytes = b"") -> Path:
    """Write a minimal file that starts with the PDF magic bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4\n" + body + path.name.encode())
    return path


@pytest.fixture
def corpus(tmp_path: Path) -> CorpusManager:
    manager = CorpusManager(tmp_path / "corpus", use_bagit=True)
    manager.create_structured_directories()
    return manager


def _pdf_dir(corpus: CorpusManager) -> Path:
    return corpus.corpus_dir / "data" / "documents" / "pdf"


class TestIngestLocalPdfDirectory:
    def test_imports_pdfs_and_writes_metadata(self, tmp_path, corpus):
        src = tmp_path / "pdfs"
        _write_pdf(src / "first paper.pdf")
        _write_pdf(src / "second.PDF")

        summary = ingest_local_pdf_directory(src, corpus)

        assert sorted(summary["added"]) == ["local_first_paper", "local_second"]
        assert (
            (_pdf_dir(corpus) / "local_first_paper.pdf")
            .read_bytes()
            .startswith(b"%PDF")
        )
        metadata = corpus.get_paper_metadata("local_first_paper")
        assert metadata["title"] == "first paper"
        assert metadata["source"] == "local"
        assert metadata["original_filename"] == "first paper.pdf"
        assert len(metadata["sha256"]) == 64
        assert sorted(corpus.list_papers()) == ["local_first_paper", "local_second"]
        assert corpus.bagit_manager.validate_bag()

    def test_skips_files_that_are_not_pdfs(self, tmp_path, corpus):
        src = tmp_path / "pdfs"
        _write_pdf(src / "good.pdf")
        (src / "fake.pdf").write_bytes(b"<html>not a pdf</html>")
        (src / "notes.txt").write_text("ignored")

        summary = ingest_local_pdf_directory(src, corpus)

        assert summary["added"] == ["local_good"]
        assert [Path(s["path"]).name for s in summary["skipped"]] == ["fake.pdf"]

    def test_reimport_does_not_duplicate(self, tmp_path, corpus):
        src = tmp_path / "pdfs"
        _write_pdf(src / "paper.pdf")
        ingest_local_pdf_directory(src, corpus)

        # Same content under another name is also a duplicate
        (src / "copy.pdf").write_bytes((src / "paper.pdf").read_bytes())
        summary = ingest_local_pdf_directory(src, corpus)

        assert summary["added"] == []
        assert len(summary["duplicates"]) == 2
        assert corpus.list_papers() == ["local_paper"]

    def test_recursive_and_id_collisions(self, tmp_path, corpus):
        src = tmp_path / "pdfs"
        _write_pdf(src / "a" / "paper.pdf", b"one")
        _write_pdf(src / "b" / "paper.pdf", b"two")

        assert ingest_local_pdf_directory(src, corpus)["added"] == []

        summary = ingest_local_pdf_directory(src, corpus, recursive=True)

        assert sorted(summary["added"]) == ["local_paper", "local_paper_2"]

    def test_reopening_corpus_keeps_layout(self, tmp_path, corpus):
        src = tmp_path / "pdfs"
        _write_pdf(src / "first.pdf")
        ingest_local_pdf_directory(src, corpus)

        reopened = CorpusManager(corpus.corpus_dir, use_bagit=True)
        _write_pdf(src / "second.pdf")
        ingest_local_pdf_directory(src, reopened)

        # Re-bagging would move documents/ and metadata/ under data/data/
        assert not (corpus.corpus_dir / "data" / "data" / "documents").exists()
        assert not (corpus.corpus_dir / "data" / "data" / "metadata").exists()
        assert sorted(reopened.list_papers()) == ["local_first", "local_second"]

    def test_missing_directory_raises(self, tmp_path, corpus):
        with pytest.raises(CorpusError):
            ingest_local_pdf_directory(tmp_path / "nope", corpus)

    def test_requires_bagit_corpus(self, tmp_path):
        src = tmp_path / "pdfs"
        src.mkdir()
        plain = CorpusManager(tmp_path / "plain")
        with pytest.raises(CorpusError):
            ingest_local_pdf_directory(src, plain)


def test_cli_import_command(tmp_path: Path):
    src = tmp_path / "pdfs"
    _write_pdf(src / "paper.pdf")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "semantic_corpus.cli",
            "import",
            "--pdf-dir",
            str(src),
            "--name",
            "mine",
            "--path",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Imported 1 PDFs" in result.stdout
    metadata_file = (
        tmp_path / "mine" / "data" / "metadata" / "local_paper_metadata.json"
    )
    assert json.loads(metadata_file.read_text(encoding="utf-8"))["source"] == "local"
