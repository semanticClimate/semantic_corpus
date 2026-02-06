"""Tests for BAGIT and structured directory support in CorpusManager."""

import pytest
from pathlib import Path
from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError


class TestCorpusManagerBagit:
    """Test cases for CorpusManager with BAGIT support."""

    def test_corpus_manager_with_bagit(self, temp_dir: Path):
        """Test creating a corpus with BAGIT support."""
        corpus_manager = CorpusManager(temp_dir, use_bagit=True)
        
        # Check BAGIT files exist
        assert Path(temp_dir, "bagit.txt").exists(), "bagit.txt should exist when use_bagit=True"
        assert Path(temp_dir, "bag-info.txt").exists(), "bag-info.txt should exist when use_bagit=True"
        assert Path(temp_dir, "data").exists(), "data directory should exist when use_bagit=True"

    def test_corpus_manager_without_bagit(self, temp_dir: Path):
        """Test creating a corpus without BAGIT (backward compatibility)."""
        corpus_manager = CorpusManager(temp_dir, use_bagit=False)
        
        # BAGIT files should not exist
        assert not Path(temp_dir, "bagit.txt").exists(), "bagit.txt should not exist when use_bagit=False"
        # But corpus directory should exist
        assert corpus_manager.corpus_dir.exists(), "Corpus directory should exist"

    def test_corpus_manager_default_no_bagit(self, temp_dir: Path):
        """Test that default behavior doesn't use BAGIT (backward compatibility)."""
        corpus_manager = CorpusManager(temp_dir)
        
        # BAGIT files should not exist by default
        assert not Path(temp_dir, "bagit.txt").exists(), "bagit.txt should not exist by default (backward compatibility)"
        # But corpus directory should exist
        assert corpus_manager.corpus_dir.exists(), "Corpus directory should exist"

    def test_create_structured_directories(self, temp_dir: Path):
        """Test creating structured corpus directories."""
        corpus_manager = CorpusManager(temp_dir, use_bagit=True)
        corpus_manager.create_structured_directories()
        
        # Check all required directories exist
        assert Path(temp_dir, "data", "documents", "pdf").exists(), "data/documents/pdf directory should exist"
        assert Path(temp_dir, "data", "documents", "xml").exists(), "data/documents/xml directory should exist"
        assert Path(temp_dir, "data", "documents", "html").exists(), "data/documents/html directory should exist"
        assert Path(temp_dir, "data", "semantic").exists(), "data/semantic directory should exist"
        assert Path(temp_dir, "data", "metadata").exists(), "data/metadata directory should exist"
        assert Path(temp_dir, "data", "keyphrases").exists(), "data/keyphrases directory should exist"
        assert Path(temp_dir, "data", "indices").exists(), "data/indices directory should exist"
        assert Path(temp_dir, "relations").exists(), "relations directory should exist"
        assert Path(temp_dir, "analysis").exists(), "analysis directory should exist"
        assert Path(temp_dir, "provenance").exists(), "provenance directory should exist"

    def test_add_paper_with_bagit_structure(self, temp_dir: Path, sample_metadata: dict):
        """Test adding a paper to a BAGIT-structured corpus."""
        corpus_manager = CorpusManager(temp_dir, use_bagit=True)
        corpus_manager.create_structured_directories()
        
        paper_id = "test_paper_001"
        result = corpus_manager.add_paper(paper_id, sample_metadata)
        
        assert result is True, "add_paper should return True"
        # Paper metadata should be in data/metadata/
        metadata_file = Path(temp_dir, "data", "metadata", f"{paper_id}_metadata.json")
        assert metadata_file.exists(), f"Metadata file {metadata_file} should exist"

    def test_backward_compatibility_add_paper(self, temp_dir: Path, sample_metadata: dict):
        """Test that add_paper still works with old structure (backward compatibility)."""
        corpus_manager = CorpusManager(temp_dir, use_bagit=False)
        
        paper_id = "test_paper_002"
        result = corpus_manager.add_paper(paper_id, sample_metadata)
        
        assert result is True, "add_paper should return True"
        # Should still work with old structure
        assert Path(temp_dir, "papers", paper_id, "metadata.json").exists(), f"Old structure metadata file should exist for {paper_id}"

    def test_get_paper_metadata_bagit_structure(self, temp_dir: Path, sample_metadata: dict):
        """Test retrieving paper metadata from BAGIT structure."""
        corpus_manager = CorpusManager(temp_dir, use_bagit=True)
        corpus_manager.create_structured_directories()
        
        paper_id = "test_paper_003"
        corpus_manager.add_paper(paper_id, sample_metadata)
        
        # Should be able to retrieve metadata
        retrieved = corpus_manager.get_paper_metadata(paper_id)
        assert retrieved == sample_metadata, f"Retrieved metadata should match sample metadata, got {retrieved}"

    def test_list_papers_bagit_structure(self, temp_dir: Path, sample_metadata: dict):
        """Test listing papers in BAGIT structure."""
        corpus_manager = CorpusManager(temp_dir, use_bagit=True)
        corpus_manager.create_structured_directories()
        
        paper_ids = ["paper_001", "paper_002", "paper_003"]
        for paper_id in paper_ids:
            corpus_manager.add_paper(paper_id, sample_metadata)
        
        papers = corpus_manager.list_papers()
        assert len(papers) == 3, f"Expected 3 papers, got {len(papers)}"
        for paper_id in paper_ids:
            assert paper_id in papers, f"Paper {paper_id} should be in papers list"




