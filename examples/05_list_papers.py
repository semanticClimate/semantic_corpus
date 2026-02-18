#!/usr/bin/env python3
"""
Example 5: List all papers in a corpus.

This example demonstrates how to list all papers in an existing corpus.
"""

from pathlib import Path
from semantic_corpus.core.corpus_manager import CorpusManager

corpus_dir = Path("corpora", "my_research")
corpus = CorpusManager(corpus_dir, use_bagit=True)

# List all papers
papers = corpus.list_papers()
print(f"Corpus contains {len(papers)} papers:")
for paper_id in papers:
    print(f"  - {paper_id}")
