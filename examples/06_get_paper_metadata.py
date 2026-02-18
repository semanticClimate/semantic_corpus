#!/usr/bin/env python3
"""
Example 6: Retrieve paper metadata from corpus.

This example demonstrates how to retrieve and display metadata for a specific paper.
"""

from pathlib import Path
from semantic_corpus.core.corpus_manager import CorpusManager
import json

corpus_dir = Path("corpora", "my_research")
corpus = CorpusManager(corpus_dir, use_bagit=True)

# Get metadata for a specific paper
paper_id = "paper_001"  # Change this to an existing paper ID
try:
    metadata = corpus.get_paper_metadata(paper_id)
    
    print(f"Title: {metadata.get('title')}")
    print(f"Authors: {', '.join(metadata.get('authors', []))}")
    print(f"DOI: {metadata.get('doi')}")
    
    # Pretty print full metadata
    print("\nFull metadata:")
    print(json.dumps(metadata, indent=2))
except Exception as e:
    print(f"Error retrieving metadata: {e}")
    print("Note: Make sure the corpus exists and contains papers. Run example 01_create_corpus.py first.")
