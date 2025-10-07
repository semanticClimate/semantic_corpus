"""Integration tests with live APIs and real downloads."""

import pytest
from pathlib import Path
from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.repository_factory import RepositoryFactory


class TestLiveIntegration:
    """Integration tests using live APIs and real downloads."""

    @pytest.mark.live_api
    @pytest.mark.network
    @pytest.mark.integration
    def test_full_workflow_europe_pmc(self, temp_dir: Path):
        """Test complete workflow with Europe PMC: search -> download -> add to corpus."""
        # Create corpus
        corpus_dir = temp_dir / "test_corpus"
        corpus_manager = CorpusManager(corpus_dir)
        
        # Get repository
        repo = RepositoryFactory.get_repository("europe_pmc")
        
        # Search for papers
        search_results = repo.search_papers(
            query="climate change adaptation",
            limit=2
        )
        
        assert len(search_results) > 0, "No search results found"
        
        # Download first paper
        first_paper = search_results[0]
        paper_id = first_paper.get("pmcid") or first_paper.get("pmid")
        assert paper_id, "No valid paper ID found"
        
        download_result = repo.download_paper(
            paper_id=paper_id,
            output_dir=temp_dir / "downloads",
            formats=["xml"]
        )
        
        assert download_result["success"] is True
        assert len(download_result["files"]) > 0
        
        # Verify files were downloaded
        for file_path in download_result["files"]:
            assert Path(file_path).exists()
            assert Path(file_path).stat().st_size > 0
        
        # Add paper to corpus
        corpus_paper_id = f"europe_pmc_{paper_id}"
        add_result = corpus_manager.add_paper(corpus_paper_id, first_paper)
        assert add_result is True
        
        # Verify paper is in corpus
        retrieved_metadata = corpus_manager.get_paper_metadata(corpus_paper_id)
        assert retrieved_metadata["title"] == first_paper["title"]
        assert retrieved_metadata["abstract"] == first_paper["abstract"]
        
        # Test search in corpus
        search_results = corpus_manager.search_papers("climate", field="title")
        assert corpus_paper_id in search_results

    @pytest.mark.live_api
    @pytest.mark.network
    @pytest.mark.integration
    def test_full_workflow_arxiv(self, temp_dir: Path):
        """Test complete workflow with arXiv: search -> download -> add to corpus."""
        # Create corpus
        corpus_dir = temp_dir / "test_corpus_arxiv"
        corpus_manager = CorpusManager(corpus_dir)
        
        # Get repository
        repo = RepositoryFactory.get_repository("arxiv")
        
        # Search for papers
        search_results = repo.search_papers(
            query="machine learning climate",
            limit=2,
            categories=["cs.AI"]
        )
        
        assert len(search_results) > 0, "No search results found"
        
        # Download first paper
        first_paper = search_results[0]
        arxiv_id = first_paper.get("arxiv_id")
        assert arxiv_id, "No valid arXiv ID found"
        
        download_result = repo.download_paper(
            paper_id=arxiv_id,
            output_dir=temp_dir / "downloads_arxiv",
            formats=["pdf"]
        )
        
        assert download_result["success"] is True
        assert len(download_result["files"]) > 0
        
        # Verify files were downloaded
        for file_path in download_result["files"]:
            assert Path(file_path).exists()
            assert Path(file_path).stat().st_size > 0
        
        # Add paper to corpus
        corpus_paper_id = f"arxiv_{arxiv_id}"
        add_result = corpus_manager.add_paper(corpus_paper_id, first_paper)
        assert add_result is True
        
        # Verify paper is in corpus
        retrieved_metadata = corpus_manager.get_paper_metadata(corpus_paper_id)
        assert retrieved_metadata["title"] == first_paper["title"]
        assert retrieved_metadata["abstract"] == first_paper["abstract"]
        
        # Test search in corpus
        search_results = corpus_manager.search_papers("machine", field="title")
        assert corpus_paper_id in search_results

    @pytest.mark.live_api
    @pytest.mark.network
    @pytest.mark.integration
    def test_corpus_statistics_with_real_papers(self, temp_dir: Path):
        """Test corpus statistics with real downloaded papers."""
        # Create corpus
        corpus_dir = temp_dir / "stats_corpus"
        corpus_manager = CorpusManager(corpus_dir)
        
        # Get repository and add some real papers
        repo = RepositoryFactory.get_repository("europe_pmc")
        
        # Search and add 3 papers
        search_results = repo.search_papers(
            query="climate change",
            limit=3
        )
        
        assert len(search_results) >= 2, "Need at least 2 papers for statistics test"
        
        for i, paper in enumerate(search_results[:2]):  # Add first 2 papers
            paper_id = paper.get("pmcid") or paper.get("pmid")
            if paper_id:
                corpus_paper_id = f"paper_{i:03d}"
                corpus_manager.add_paper(corpus_paper_id, paper)
        
        # Get statistics
        stats = corpus_manager.get_statistics()
        
        assert stats["total_papers"] == 2
        assert stats["corpus_size_mb"] > 0
        assert "creation_date" in stats
        assert "last_updated" in stats

    def test_repository_info(self):
        """Test getting repository information."""
        # Test Europe PMC info
        europe_pmc = RepositoryFactory.get_repository("europe_pmc")
        info = europe_pmc.get_repository_info()
        
        assert info["name"] == "Europe PMC"
        assert "base_url" in info
        assert "description" in info
        assert "supported_formats" in info
        assert "xml" in info["supported_formats"]
        
        # Test arXiv info
        arxiv = RepositoryFactory.get_repository("arxiv")
        info = arxiv.get_repository_info()
        
        assert info["name"] == "arXiv"
        assert "base_url" in info
        assert "description" in info
        assert "supported_formats" in info
        assert "pdf" in info["supported_formats"]

    def test_error_handling_with_live_apis(self):
        """Test error handling with live APIs."""
        # Test invalid repository
        with pytest.raises(Exception):  # Should raise RepositoryError
            RepositoryFactory.get_repository("invalid_repository")
        
        # Test invalid paper ID
        repo = RepositoryFactory.get_repository("europe_pmc")
        with pytest.raises(Exception):  # Should raise RepositoryError
            repo.get_paper_metadata("INVALID_ID_12345")
        
        # Test invalid arXiv ID
        arxiv_repo = RepositoryFactory.get_repository("arxiv")
        with pytest.raises(Exception):  # Should raise RepositoryError
            arxiv_repo.get_paper_metadata("9999.9999")
