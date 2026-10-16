"""Factory for creating repository instances."""

from typing import Dict, List, Type
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.repositories.europe_pmc import EuropePMCRepository
from semantic_corpus.repositories.arxiv import ArxivRepository


class RepositoryFactory:
    """Factory class for creating repository instances.
    A repository is a foreign source of papers  such as Europe PMC or arXiv.
    """

    _repositories: Dict[str, Type[RepositoryInterface]] = {
        "europe_pmc": EuropePMCRepository,
        "arxiv": ArxivRepository,
    }

    @classmethod
    def get_repository(cls, name: str) -> RepositoryInterface:
        """Get a repository instance by name.
        
        Args:
            name: Repository name
            
        Returns:
            Repository instance
            
        Raises:
            RepositoryError: If repository not found
        """
        if name not in cls._repositories:
            available = ", ".join(cls._repositories.keys())
            raise RepositoryError(
                f"Repository '{name}' not found. Available repositories: {available}"
            )
        
        return cls._repositories[name]()

    @classmethod
    def list_repositories(cls) -> List[str]:
        """List all available repository names.
        
        Returns:
            List of repository names
        """
        return list(cls._repositories.keys())

    @classmethod
    def register_repository(cls, name: str, repository_class: Type[RepositoryInterface]) -> None:
        """Register a new repository class.
        
        Args:
            name: Repository name
            repository_class: Repository class to register
        """
        cls._repositories[name] = repository_class
