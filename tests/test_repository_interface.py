"""Tests for repository interface functionality."""

import pytest
from pathlib import Path
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.repositories.europe_pmc import EuropePMCRepository
from semantic_corpus.repositories.arxiv import ArxivRepository


class TestRepositoryInterface:
    """Test cases for RepositoryInterface abstract base class."""

    def test_repository_interface_is_abstract(self):
        """Test that RepositoryInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RepositoryInterface()

    def test_repository_interface_has_required_methods(self):
        """Test that RepositoryInterface defines required abstract methods."""
        # Check that the abstract methods exist
        assert hasattr(RepositoryInterface, 'search_papers')
        assert hasattr(RepositoryInterface, 'download_paper')
        assert hasattr(RepositoryInterface, 'get_paper_metadata')
        assert hasattr(RepositoryInterface, 'get_repository_info')


class TestEuropePMCRepository:
    """Test cases for Europe PMC repository implementation."""

    def test_europe_pmc_initialization(self):
        """Test that Europe PMC repository can be initialized."""
        repo = EuropePMCRepository()
        assert repo.name == "Europe PMC"
        assert repo.base_url == "https://www.ebi.ac.uk/europepmc/webservices/rest"

    @pytest.mark.live_api
    @pytest.mark.network
    def test_europe_pmc_search_papers(self):
        """Test searching papers in Europe PMC with live API."""
        repo = EuropePMCRepository()
        
        # Use live API with a simple, reliable query
        results = repo.search_papers(
            query="climate change",
            limit=3,
            start_date="2023-01-01",
            end_date="2024-01-01"
        )
        
        assert isinstance(results, list)
        assert len(results) <= 3
        for result in results:
            assert "pmcid" in result or "pmid" in result
            assert "title" in result
            assert "abstract" in result
            # Verify we got real data
            assert result["title"] != ""
            assert result["abstract"] != ""

    @pytest.mark.live_api
    @pytest.mark.network
    def test_europe_pmc_get_paper_metadata(self):
        """Test getting paper metadata from Europe PMC with live API."""
        repo = EuropePMCRepository()
        
        # Use a known working paper ID
        paper_id = "40964903"  # PMID that we know works
        
        # Test getting metadata for the real paper
        metadata = repo.get_paper_metadata(paper_id)
        
        assert isinstance(metadata, dict)
        assert "title" in metadata
        assert "abstract" in metadata
        assert "authors" in metadata
        assert "publication_date" in metadata
        # Verify we got real data
        assert metadata["title"] != ""
        assert metadata["abstract"] != ""

    @pytest.mark.live_api
    @pytest.mark.network
    def test_europe_pmc_download_paper(self, temp_dir: Path):
        """Test downloading a paper from Europe PMC with live API."""
        repo = EuropePMCRepository()
        
        # Use a known working paper ID
        paper_id = "40964903"  # PMID that we know works
        
        # Test downloading the real paper to corpora directory
        result = repo.download_paper(
            paper_id=paper_id,
            output_dir=temp_dir,
            formats=["xml"]  # Start with XML only for faster testing
        )
        
        assert result["success"] is True
        assert "files" in result
        assert len(result["files"]) > 0
        
        # Verify files were actually downloaded
        for file_path in result["files"]:
            assert Path(file_path).exists()
            assert Path(file_path).stat().st_size > 0


class TestArxivRepository:
    """Test cases for arXiv repository implementation."""

    def test_arxiv_initialization(self):
        """Test that arXiv repository can be initialized."""
        repo = ArxivRepository()
        assert repo.name == "arXiv"
        assert repo.base_url == "http://export.arxiv.org/api/query"

    @pytest.mark.live_api
    @pytest.mark.network
    @pytest.mark.arxiv
    def test_arxiv_search_papers(self):
        """Test searching papers in arXiv with live API."""
        repo = ArxivRepository()
        
        # Use a simple query that should return results
        results = repo.search_papers(
            query="machine learning",
            limit=3
        )
        
        assert isinstance(results, list)
        # If no results with categories, try without categories
        if len(results) == 0:
            results = repo.search_papers(
                query="climate",
                limit=3
            )
        
        # If still no results, skip the test (arXiv might be blocking)
        if len(results) == 0:
            pytest.skip("arXiv API returned no results - may be rate limited or blocked")
        
        assert len(results) <= 3
        for result in results:
            assert "arxiv_id" in result
            assert "title" in result
            assert "abstract" in result
            # Verify we got real data
            assert result["title"] != ""
            assert result["abstract"] != ""
            assert result["arxiv_id"] != ""

    @pytest.mark.live_api
    @pytest.mark.network
    @pytest.mark.arxiv
    def test_arxiv_get_paper_metadata(self):
        """Test getting paper metadata from arXiv with live API."""
        repo = ArxivRepository()
        
        # First search for a real paper to get a valid arXiv ID
        search_results = repo.search_papers(query="machine learning", limit=1)
        
        # If no results, try a different query
        if len(search_results) == 0:
            search_results = repo.search_papers(query="climate", limit=1)
        
        # If still no results, skip the test
        if len(search_results) == 0:
            pytest.skip("arXiv API returned no results - may be rate limited or blocked")
        
        # Get the first paper's arXiv ID
        arxiv_id = search_results[0].get("arxiv_id")
        assert arxiv_id, "No valid arXiv ID found in search results"
        
        # Test getting metadata for the real paper
        metadata = repo.get_paper_metadata(arxiv_id)
        
        assert isinstance(metadata, dict)
        assert "title" in metadata
        assert "abstract" in metadata
        assert "authors" in metadata
        assert "publication_date" in metadata
        # Verify we got real data
        assert metadata["title"] != ""
        assert metadata["abstract"] != ""

    @pytest.mark.live_api
    @pytest.mark.network
    @pytest.mark.arxiv
    def test_arxiv_download_paper(self, temp_dir: Path):
        """Test downloading a paper from arXiv with live API."""
        repo = ArxivRepository()
        
        # First search for a real paper to get a valid arXiv ID
        search_results = repo.search_papers(query="machine learning", limit=1)
        
        # If no results, try a different query
        if len(search_results) == 0:
            search_results = repo.search_papers(query="climate", limit=1)
        
        # If still no results, skip the test
        if len(search_results) == 0:
            pytest.skip("arXiv API returned no results - may be rate limited or blocked")
        
        # Get the first paper's arXiv ID
        arxiv_id = search_results[0].get("arxiv_id")
        assert arxiv_id, "No valid arXiv ID found in search results"
        
        # Test downloading the real paper to corpora directory
        result = repo.download_paper(
            paper_id=arxiv_id,
            output_dir=temp_dir,
            formats=["pdf"]
        )
        
        assert result["success"] is True
        assert "files" in result
        assert len(result["files"]) > 0
        
        # Verify files were actually downloaded
        for file_path in result["files"]:
            assert Path(file_path).exists()
            assert Path(file_path).stat().st_size > 0


class TestRepositoryFactory:
    """Test cases for repository factory pattern."""

    def test_get_repository_by_name(self):
        """Test getting repository by name."""
        from semantic_corpus.core.repository_factory import RepositoryFactory
        
        # Test getting Europe PMC repository
        repo = RepositoryFactory.get_repository("europe_pmc")
        assert isinstance(repo, EuropePMCRepository)
        
        # Test getting arXiv repository
        repo = RepositoryFactory.get_repository("arxiv")
        assert isinstance(repo, ArxivRepository)

    def test_get_repository_raises_error_for_unknown(self):
        """Test that getting unknown repository raises error."""
        from semantic_corpus.core.repository_factory import RepositoryFactory
        
        with pytest.raises(RepositoryError):
            RepositoryFactory.get_repository("unknown_repository")

    def test_list_available_repositories(self):
        """Test listing available repositories."""
        from semantic_corpus.core.repository_factory import RepositoryFactory
        
        repositories = RepositoryFactory.list_repositories()
        
        assert isinstance(repositories, list)
        assert "europe_pmc" in repositories
        assert "arxiv" in repositories
        assert len(repositories) >= 2
