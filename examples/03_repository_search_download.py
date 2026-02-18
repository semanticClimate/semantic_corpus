#!/usr/bin/env python3
"""
Example 3: Repository operations - search and download papers.

This example demonstrates how to search for papers and download them from repositories.
"""

from pathlib import Path
from semantic_corpus.core.repository_factory import RepositoryFactory

# Get repository
repo = RepositoryFactory.get_repository("europe_pmc")

# Search papers
results = repo.search_papers(
    query="climate change adaptation",
    limit=10
)

print(f"Found {len(results)} papers")
for i, paper in enumerate(results[:3], 1):  # Show first 3
    print(f"{i}. {paper.get('title', 'No title')}")

# Download a paper (if results found)
if results:
    paper_id = results[0].get("pmcid") or results[0].get("pmid")
    if paper_id:
        download_dir = Path("temp", "downloads")
        download_dir.mkdir(parents=True, exist_ok=True)
        
        download_result = repo.download_paper(
            paper_id=paper_id,
            output_dir=download_dir,
            formats=["xml"]
        )
        
        if download_result["success"]:
            print(f"\nDownloaded paper {paper_id}")
            print(f"Files: {download_result['files']}")
        else:
            print(f"\nFailed to download paper {paper_id}")
