"""Custom exceptions for semantic_corpus."""

from typing import Optional


class SemanticCorpusError(Exception):
    """Base exception for semantic_corpus."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class CorpusError(SemanticCorpusError):
    """Exception raised for corpus-related errors."""

    pass


class RepositoryError(SemanticCorpusError):
    """Exception raised for repository-related errors."""

    def __init__(
        self, message: str, *, status_code: Optional[int] = None
    ) -> None:
        self.status_code = status_code
        super().__init__(message)


class MetadataError(SemanticCorpusError):
    """Exception raised for metadata-related errors."""

    pass


class DownloadError(SemanticCorpusError):
    """Exception raised for download-related errors."""

    pass


class ValidationError(SemanticCorpusError):
    """Exception raised for validation-related errors."""

    pass
