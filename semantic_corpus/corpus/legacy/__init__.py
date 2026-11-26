"""Legacy document converter: extractor → sectioner → indexed_text."""

from semantic_corpus.corpus.legacy.extractors import (
    AVAILABLE_EXTRACTORS,
    list_extractors,
)
from semantic_corpus.corpus.legacy.pipeline import legacy_to_indexed_text

__all__ = [
    "AVAILABLE_EXTRACTORS",
    "legacy_to_indexed_text",
    "list_extractors",
]
