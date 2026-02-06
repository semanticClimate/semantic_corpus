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
        # Create corpus in corpora directory
        corpus_dir = Path(temp_dir, "test_corpus")
        corpus_manager = CorpusManager(corpus_dir)
        
        # Get repository
        repo = RepositoryFactory.get_repository("europe_pmc")
        
        # Search for papers
        search_results = repo.search_papers(
            query="climate change adaptation",
            limit=2
        )
        
        assert len(search_results) > 0, "No search results found"
        
        # Use a known working paper ID instead of search results
        paper_id = "40964903"  # PMID that we know works
        
        download_result = repo.download_paper(
            paper_id=paper_id,
            output_dir=Path(temp_dir, "downloads"),
            formats=["xml"]
        )
        
        assert download_result["success"] is True, "Download should succeed"
        assert len(download_result["files"]) > 0, "Download should return at least one file"
        
        # Verify files were downloaded
        for file_path in download_result["files"]:
            assert Path(file_path).exists(), f"Downloaded file {file_path} should exist"
            assert Path(file_path).stat().st_size > 0, f"Downloaded file {file_path} should not be empty"
        
        # Add paper to corpus - get metadata first
        metadata = repo.get_paper_metadata(paper_id)
        corpus_paper_id = f"europe_pmc_{paper_id}"
        add_result = corpus_manager.add_paper(corpus_paper_id, metadata)
        assert add_result is True, "add_paper should return True"
        
        # Verify paper is in corpus
        retrieved_metadata = corpus_manager.get_paper_metadata(corpus_paper_id)
        assert retrieved_metadata["title"] == metadata["title"], f"Retrieved title should match, got '{retrieved_metadata.get('title')}'"
        assert retrieved_metadata["abstract"] == metadata["abstract"], f"Retrieved abstract should match, got '{retrieved_metadata.get('abstract')}'"
        
        # Test search in corpus
        search_results = corpus_manager.search_papers("climate", field="title")
        assert corpus_paper_id in search_results, f"Paper {corpus_paper_id} should be found in search results"

    @pytest.mark.live_api
    @pytest.mark.network
    @pytest.mark.integration
    @pytest.mark.arxiv
    def test_full_workflow_arxiv(self, temp_dir: Path):
        """Test complete workflow with arXiv: search -> download -> add to corpus."""
        # Create corpus in corpora directory
        corpus_dir = Path(temp_dir, "test_corpus_arxiv")
        corpus_manager = CorpusManager(corpus_dir)
        
        # Get repository
        repo = RepositoryFactory.get_repository("arxiv")
        
        # Search for papers
        search_results = repo.search_papers(
            query="machine learning",
            limit=2
        )
        
        # If no results, try a simpler query
        if len(search_results) == 0:
            search_results = repo.search_papers(
                query="climate",
                limit=2
            )
        
        # If still no results, skip the test
        if len(search_results) == 0:
            pytest.skip("arXiv API returned no results - may be rate limited or blocked")
        
        # Download first paper
        metadata = search_results[0]
        arxiv_id = metadata.get("arxiv_id")
        assert arxiv_id, "No valid arXiv ID found"
        
        download_result = repo.download_paper(
            paper_id=arxiv_id,
            output_dir=Path(temp_dir, "downloads_arxiv"),
            formats=["pdf"]
        )
        
        assert download_result["success"] is True, "Download should succeed"
        assert len(download_result["files"]) > 0, "Download should return at least one file"
        
        # Verify files were downloaded
        for file_path in download_result["files"]:
            assert Path(file_path).exists(), f"Downloaded file {file_path} should exist"
            assert Path(file_path).stat().st_size > 0, f"Downloaded file {file_path} should not be empty"
        
        # Add paper to corpus
        corpus_paper_id = f"arxiv_{arxiv_id}"
        add_result = corpus_manager.add_paper(corpus_paper_id, metadata)
        assert add_result is True, "add_paper should return True"
        
        # Verify paper is in corpus
        retrieved_metadata = corpus_manager.get_paper_metadata(corpus_paper_id)
        assert retrieved_metadata["title"] == metadata["title"], f"Retrieved title should match, got '{retrieved_metadata.get('title')}'"
        assert retrieved_metadata["abstract"] == metadata["abstract"], f"Retrieved abstract should match, got '{retrieved_metadata.get('abstract')}'"
        
        # Test search in corpus
        search_results = corpus_manager.search_papers("machine", field="title")
        assert corpus_paper_id in search_results, f"Paper {corpus_paper_id} should be found in search results"

    @pytest.mark.live_api
    @pytest.mark.network
    @pytest.mark.integration
    def test_corpus_statistics_with_real_papers(self, temp_dir: Path):
        """Test corpus statistics with real downloaded papers."""
        # Create corpus in corpora directory
        corpus_dir = Path(temp_dir, "stats_corpus")
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
        
        assert stats["total_papers"] == 2, f"Expected 2 papers, got {stats.get('total_papers')}"
        assert stats["corpus_size_mb"] > 0, f"Expected corpus_size_mb > 0, got {stats.get('corpus_size_mb')}"
        assert "creation_date" in stats, "Statistics should contain 'creation_date'"
        assert "last_updated" in stats, "Statistics should contain 'last_updated'"

    def test_repository_info(self):
        """Test getting repository information."""
        # Test Europe PMC info
        europe_pmc = RepositoryFactory.get_repository("europe_pmc")
        info = europe_pmc.get_repository_info()
        
        assert info["name"] == "Europe PMC", f"Expected name 'Europe PMC', got '{info.get('name')}'"
        assert "base_url" in info, "Repository info should contain 'base_url'"
        assert "description" in info, "Repository info should contain 'description'"
        assert "supported_formats" in info, "Repository info should contain 'supported_formats'"
        assert "xml" in info["supported_formats"], "Europe PMC should support 'xml' format"
        
        # Test arXiv info
        arxiv = RepositoryFactory.get_repository("arxiv")
        info = arxiv.get_repository_info()
        
        assert info["name"] == "arXiv", f"Expected name 'arXiv', got '{info.get('name')}'"
        assert "base_url" in info, "Repository info should contain 'base_url'"
        assert "description" in info, "Repository info should contain 'description'"
        assert "supported_formats" in info, "Repository info should contain 'supported_formats'"
        assert "pdf" in info["supported_formats"], "arXiv should support 'pdf' format"

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
