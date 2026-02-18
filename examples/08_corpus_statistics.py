#!/usr/bin/env python3
"""
Example 8: Get corpus statistics.

This example demonstrates how to retrieve and display corpus statistics.
"""

from pathlib import Path
from semantic_corpus.core.corpus_manager import CorpusManager
import json

corpus_dir = Path("corpora", "my_research")
corpus = CorpusManager(corpus_dir, use_bagit=True)

# Get statistics
stats = corpus.get_statistics()
print("Corpus Statistics:")
print(json.dumps(stats, indent=2))
