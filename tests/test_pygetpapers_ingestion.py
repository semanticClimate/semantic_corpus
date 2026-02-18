"""
Tests for ingesting classic pygetpapers output directories into semantic_corpus.

Test data: ../amilib/test/resources/pygetpapers/wildlife/
- Classic Europe PMC pygetpapers output: per-article folders PMC<id> with
  eupmc_result.json and fulltext.xml (and optionally fulltext.pdf).
- Tests require the amilib repo as a sibling of semantic_corpus so that
  path resolves. If the wildlife directory is missing, ingestion tests are skipped.
"""

import pytest
from pathlib import Path

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.ingestion.pygetpapers_ingester import (
    _discover_paper_folders,
    _eupmc_json_to_raw_metadata,
    ingest_pygetpapers_directory,
)


def _wildlife_dir() -> Path:
    """Path to amilib pygetpapers wildlife fixture (sibling repo)."""
    # semantic_corpus repo root is parent of tests/
    repo_root = Path(__file__).resolve().parent.parent
    return Path(repo_root, "..", "amilib", "test", "resources", "pygetpapers", "wildlife").resolve()


@pytest.fixture
def pygetpapers_wildlife_dir() -> Path:
    """Path to ../amilib/test/resources/pygetpapers/wildlife/. Skips if missing."""
    path = _wildlife_dir()
    if not path.exists() or not path.is_dir():
        pytest.skip(
            f"Pygetpapers wildlife fixture not found: {path}. "
            "Need amilib repo as sibling with test/resources/pygetpapers/wildlife/."
        )
    return path


class TestPygetpapersIngestion:
    """Ingest pygetpapers wildlife directory into a BAGIT corpus."""

    def test_ingest_wildlife_adds_all_papers(
        self, temp_dir: Path, pygetpapers_wildlife_dir: Path
    ) -> None:
        """Ingesting wildlife dir adds one corpus paper per PMC folder."""
        corpus = CorpusManager(temp_dir, use_bagit=True)
        corpus.create_structured_directories()
        added = ingest_pygetpapers_directory(pygetpapers_wildlife_dir, corpus)
        papers = corpus.list_papers()
        assert len(added) >= 9, (
            f"Expected at least 9 papers added from wildlife dir, got {len(added)}"
        )
        assert len(papers) == len(added), (
            f"Corpus list_papers() should match number added, got {len(papers)} vs {len(added)}"
        )
        for pid in added:
            assert pid in papers, f"Added paper {pid} should be in list_papers()"

    def test_ingest_wildlife_metadata_and_xml_present(
        self, temp_dir: Path, pygetpapers_wildlife_dir: Path
    ) -> None:
        """After ingest, metadata and XML files are present for a known paper."""
        corpus = CorpusManager(temp_dir, use_bagit=True)
        corpus.create_structured_directories()
        ingest_pygetpapers_directory(pygetpapers_wildlife_dir, corpus)
        paper_id = "europe_pmc_PMC12124168"
        metadata = corpus.get_paper_metadata(paper_id)
        assert metadata.get("title"), (
            f"Metadata for {paper_id} should have title"
        )
        assert "wildlife" in (metadata.get("title") or "").lower() or "urbanization" in (metadata.get("title") or "").lower(), (
            f"Expected wildlife/urbanization-related title for {paper_id}"
        )
        assert metadata.get("abstract"), (
            f"Metadata for {paper_id} should have abstract"
        )
        assert metadata.get("doi") == "10.1111/cobi.70049", (
            f"DOI for {paper_id} should match source"
        )
        xml_path = Path(temp_dir, "data", "documents", "xml", f"{paper_id}.xml")
        assert xml_path.exists(), (
            f"XML file should exist at {xml_path} after ingest"
        )
        assert xml_path.stat().st_size > 0, (
            f"XML file {xml_path} should be non-empty"
        )

    def test_ingest_wildlife_search_after_ingest(
        self, temp_dir: Path, pygetpapers_wildlife_dir: Path
    ) -> None:
        """Search by title returns expected paper after ingest."""
        corpus = CorpusManager(temp_dir, use_bagit=True)
        corpus.create_structured_directories()
        ingest_pygetpapers_directory(pygetpapers_wildlife_dir, corpus)
        results = corpus.search_papers("wildlife", field="title")
        assert len(results) >= 1, (
            f"Search for 'wildlife' in title should return at least one paper, got {results}"
        )
        results_abstract = corpus.search_papers("conservation", field="abstract")
        assert len(results_abstract) >= 1, (
            f"Search for 'conservation' in abstract should return at least one paper, got {results_abstract}"
        )

    def test_ingest_nonexistent_dir_raises(self, temp_dir: Path) -> None:
        """Passing a non-existent directory raises CorpusError."""
        corpus = CorpusManager(temp_dir, use_bagit=True)
        corpus.create_structured_directories()
        bad_path = Path(temp_dir, "does", "not", "exist")
        with pytest.raises(CorpusError) as exc_info:
            ingest_pygetpapers_directory(bad_path, corpus)
        assert "does not exist" in str(exc_info.value), (
            "Error message should mention directory does not exist"
        )

    def test_ingest_requires_bagit(self, temp_dir: Path, pygetpapers_wildlife_dir: Path) -> None:
        """Ingestion requires BAGIT corpus; non-BAGIT raises CorpusError."""
        corpus = CorpusManager(temp_dir, use_bagit=False)
        with pytest.raises(CorpusError) as exc_info:
            ingest_pygetpapers_directory(pygetpapers_wildlife_dir, corpus)
        assert "BAGIT" in str(exc_info.value), (
            "Error message should require BAGIT"
        )


class TestPygetpapersIngestionHelpers:
    """Unit-style tests for ingester helpers."""

    def test_discover_paper_folders_wildlife(self, pygetpapers_wildlife_dir: Path) -> None:
        """_discover_paper_folders finds all PMC folders in wildlife (e.g. 10)."""
        folders = _discover_paper_folders(pygetpapers_wildlife_dir)
        assert len(folders) >= 9, (
            f"Expected at least 9 PMC folders in wildlife dir, got {len(folders)}"
        )
        names = [f.name for f in folders]
        assert "PMC12124168" in names, "PMC12124168 should be among discovered folders"

    def test_eupmc_json_to_raw_metadata(self) -> None:
        """_eupmc_json_to_raw_metadata maps Europe PMC JSON to raw dict for normalization."""
        data = {
            "title": "Test Title",
            "abstractText": "Test abstract.",
            "doi": "10.1234/test",
            "authorString": "Author A, Author B.",
            "firstPublicationDate": "2025-01-15",
            "pmcid": "PMC99999",
            "pmid": "12345",
            "journalInfo": {"journal": {"title": "Test Journal"}},
        }
        raw = _eupmc_json_to_raw_metadata(data)
        assert raw["title"] == "Test Title"
        assert raw["abstract"] == "Test abstract."
        assert raw["doi"] == "10.1234/test"
        assert raw["authors"] == ["Author A", "Author B"]
        assert raw["publication_date"] == "2025-01-15"
        assert raw["journal"] == "Test Journal"
