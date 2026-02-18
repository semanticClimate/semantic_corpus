#!/usr/bin/env python3
"""
Example 7: Search papers in corpus.

This example demonstrates how to search for papers by title or abstract.
"""

from pathlib import Path
from semantic_corpus.core.corpus_manager import CorpusManager

corpus_dir = Path("corpora", "my_research")
corpus = CorpusManager(corpus_dir, use_bagit=True)

# Search by title
results = corpus.search_papers("climate", field="title")
print(f"Found {len(results)} papers with 'climate' in title:")
for paper_id in results:
    try:
        metadata = corpus.get_paper_metadata(paper_id)
        print(f"  - {paper_id}: {metadata.get('title')}")
    except Exception:
        print(f"  - {paper_id}")

# Search by abstract
results = corpus.search_papers("adaptation", field="abstract")
print(f"\nFound {len(results)} papers with 'adaptation' in abstract")
