#!/usr/bin/env python3
"""
Example 1: Create a corpus with BAGIT support.

This example demonstrates how to create a new corpus with BAGIT-compliant structure.
"""

from pathlib import Path
from semantic_corpus.core.corpus_manager import CorpusManager

# Create corpus with BAGIT support
corpus_dir = Path("corpora", "my_research")
corpus = CorpusManager(corpus_dir, use_bagit=True)
corpus.create_structured_directories()

# Add a paper
metadata = {
    "title": "Climate Change Adaptation",
    "authors": ["Smith, J.", "Doe, A."],
    "doi": "10.1234/example",
    "publication_date": "2024-01-15"
}
corpus.add_paper("paper_001", metadata)

# Retrieve metadata
paper_meta = corpus.get_paper_metadata("paper_001")
print(f"Added paper: {paper_meta['title']}")

# List all papers
papers = corpus.list_papers()
print(f"Corpus contains {len(papers)} papers")
