#!/usr/bin/env python3
"""
Example 9: Complete ingestion workflow from Europe PMC.

This example demonstrates a complete workflow: search -> download -> add to corpus.
"""

from pathlib import Path
from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.tools.metadata_processor import MetadataProcessor
import json

# Create corpus
corpus_dir = Path("corpora", "climate_adaptation")
corpus = CorpusManager(corpus_dir, use_bagit=True)
corpus.create_structured_directories()

# Get repository
repo = RepositoryFactory.get_repository("europe_pmc")
processor = MetadataProcessor()

# Search for papers
print("Searching for papers...")
search_results = repo.search_papers(
    query="climate change adaptation",
    limit=5  # Reduced for example
)

print(f"Found {len(search_results)} papers")

# Process each paper
for paper in search_results:
    paper_id = paper.get("pmcid") or paper.get("pmid")
    if not paper_id:
        continue
    
    # Download if not already downloaded
    download_dir = Path("temp", "downloads")
    download_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        download_result = repo.download_paper(
            paper_id, download_dir, formats=["xml"]
        )
        
        # Extract metadata
        xml_file = Path(download_dir, f"{paper_id}.xml")
        if xml_file.exists():
            metadata = processor.process_xml_metadata(xml_file)
            normalized = processor.normalize_metadata(metadata)
            
            # Add to corpus
            corpus_id = f"europe_pmc_{paper_id}"
            corpus.add_paper(corpus_id, normalized)
            
            # Copy file to corpus
            corpus_xml = Path(corpus_dir, "data", "documents", "xml", f"{corpus_id}.xml")
            corpus_xml.parent.mkdir(parents=True, exist_ok=True)
            corpus_xml.write_bytes(xml_file.read_bytes())
            
            print(f"Added {corpus_id} to corpus")
    except Exception as e:
        print(f"Failed to process {paper_id}: {e}")

print(f"\nCorpus now contains {len(corpus.list_papers())} papers")
