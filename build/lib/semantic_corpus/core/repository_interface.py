"""Repository interface for different paper sources."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional

from semantic_corpus.core.exceptions import RepositoryError


class RepositoryInterface(ABC):
    """Abstract base class for paper repositories."""

    def __init__(self) -> None:
        """Initialize repository interface."""
        self.name: str = ""
        self.base_url: str = ""

    @abstractmethod
    def search_papers(
        self,
        query: str,
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Search for papers in the repository.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            start_date: Start date for search (YYYY-MM-DD)
            end_date: End date for search (YYYY-MM-DD)
            **kwargs: Additional repository-specific parameters
            
        Returns:
            List of paper metadata dictionaries
            
        Raises:
            RepositoryError: If search fails
        """
        pass

    @abstractmethod
    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Get metadata for a specific paper.
        
        Args:
            paper_id: Unique identifier for the paper
            
        Returns:
            Paper metadata dictionary
            
        Raises:
            RepositoryError: If paper not found or metadata cannot be retrieved
        """
        pass

    @abstractmethod
    def download_paper(
        self,
        paper_id: str,
        output_dir: Path,
        formats: List[str] = None
    ) -> Dict[str, Any]:
        """Download a paper and its associated files.
        
        Args:
            paper_id: Unique identifier for the paper
            output_dir: Directory to save downloaded files
            formats: List of formats to download (e.g., ['xml', 'pdf'])
            
        Returns:
            Dictionary with download results
            
        Raises:
            RepositoryError: If download fails
        """
        pass

    @abstractmethod
    def get_repository_info(self) -> Dict[str, Any]:
        """Get information about the repository.
        
        Returns:
            Dictionary with repository information
        """
        pass
