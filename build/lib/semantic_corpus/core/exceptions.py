"""Custom exceptions for semantic_corpus."""


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

    pass


class MetadataError(SemanticCorpusError):
    """Exception raised for metadata-related errors."""

    pass


class DownloadError(SemanticCorpusError):
    """Exception raised for download-related errors."""

    pass


class ValidationError(SemanticCorpusError):
    """Exception raised for validation-related errors."""

    pass
