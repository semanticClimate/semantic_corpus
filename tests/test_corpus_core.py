"""Tests for core corpus functionality."""

import pytest
from pathlib import Path
from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError


class TestCorpusManager:
    """Test cases for CorpusManager class."""

    def test_corpus_manager_initialization(self, temp_dir: Path):
        """Test that CorpusManager can be initialized with a valid directory."""
        # Create corpus in corpora directory
        corpus_manager = CorpusManager(temp_dir)
        assert corpus_manager.corpus_dir == temp_dir
        assert corpus_manager.corpus_dir.exists()

    def test_corpus_manager_creates_directory(self, temp_dir: Path):
        """Test that CorpusManager creates the corpus directory if it doesn't exist."""
        # Create new corpus directory in corpora folder
        new_dir = temp_dir / "new_corpus"
        corpus_manager = CorpusManager(new_dir)
        assert new_dir.exists()
        assert corpus_manager.corpus_dir == new_dir

    def test_corpus_manager_raises_error_for_invalid_path(self):
        """Test that CorpusManager raises error for invalid paths."""
        with pytest.raises(CorpusError):
            CorpusManager(Path("/invalid/path/that/does/not/exist"))

    def test_add_paper_to_corpus(self, temp_dir: Path, sample_metadata: dict):
        """Test adding a paper to the corpus."""
        # Create corpus in corpora directory
        corpus_manager = CorpusManager(temp_dir)
        paper_id = "test_paper_001"
        
        result = corpus_manager.add_paper(paper_id, sample_metadata)
        
        assert result is True
        assert (temp_dir / "papers" / paper_id).exists()
        assert (temp_dir / "papers" / paper_id / "metadata.json").exists()

    def test_get_paper_metadata(self, temp_dir: Path, sample_metadata: dict):
        """Test retrieving paper metadata from corpus."""
        # Create corpus in corpora directory
        corpus_manager = CorpusManager(temp_dir)
        paper_id = "test_paper_002"
        
        # Add paper first
        corpus_manager.add_paper(paper_id, sample_metadata)
        
        # Retrieve metadata
        retrieved_metadata = corpus_manager.get_paper_metadata(paper_id)
        
        assert retrieved_metadata == sample_metadata

    def test_list_papers_in_corpus(self, temp_dir: Path, sample_metadata: dict):
        """Test listing all papers in the corpus."""
        # Create corpus in corpora directory
        corpus_manager = CorpusManager(temp_dir)
        
        # Add multiple papers
        paper_ids = ["paper_001", "paper_002", "paper_003"]
        for paper_id in paper_ids:
            corpus_manager.add_paper(paper_id, sample_metadata)
        
        # List papers
        papers = corpus_manager.list_papers()
        
        assert len(papers) == 3
        for paper_id in paper_ids:
            assert paper_id in papers

    def test_search_papers_by_title(self, temp_dir: Path):
        """Test searching papers by title."""
        # Create corpus in corpora directory
        corpus_manager = CorpusManager(temp_dir)
        
        # Add papers with different titles
        papers = [
            ("paper_001", {"title": "Climate Change and Adaptation", "doi": "10.1000/001"}),
            ("paper_002", {"title": "Machine Learning Applications", "doi": "10.1000/002"}),
            ("paper_003", {"title": "Climate Change Mitigation", "doi": "10.1000/003"}),
        ]
        
        for paper_id, metadata in papers:
            corpus_manager.add_paper(paper_id, metadata)
        
        # Search for climate-related papers
        results = corpus_manager.search_papers(query="climate", field="title")
        
        assert len(results) == 2
        assert "paper_001" in results
        assert "paper_003" in results
        assert "paper_002" not in results

    def test_corpus_statistics(self, temp_dir: Path, sample_metadata: dict):
        """Test getting corpus statistics."""
        # Create corpus in corpora directory
        corpus_manager = CorpusManager(temp_dir)
        
        # Add some papers
        for i in range(5):
            paper_id = f"paper_{i:03d}"
            corpus_manager.add_paper(paper_id, sample_metadata)
        
        stats = corpus_manager.get_statistics()
        
        assert stats["total_papers"] == 5
        assert stats["corpus_size_mb"] > 0
        assert "creation_date" in stats
        assert "last_updated" in stats
