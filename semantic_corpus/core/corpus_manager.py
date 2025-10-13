"""Core corpus management functionality."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from semantic_corpus.core.exceptions import CorpusError


class CorpusManager:
    """Manages scientific paper corpora."""

    def __init__(self, corpus_dir: Path) -> None:
        """Initialize corpus manager with a directory.
        
        Args:
            corpus_dir: Path to the corpus directory
            
        Raises:
            CorpusError: If the directory cannot be created or accessed
        """
        self.corpus_dir = Path(corpus_dir)
        
        # Validate parent directory exists for invalid paths
        if not self.corpus_dir.parent.exists():
            raise CorpusError(f"Parent directory does not exist: {self.corpus_dir.parent}")
        
        # Create directory if it doesn't exist
        try:
            self.corpus_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise CorpusError(f"Cannot create corpus directory: {e}")

    def add_paper(self, paper_id: str, metadata: Dict[str, Any]) -> bool:
        """Add a paper to the corpus.
        
        Args:
            paper_id: Unique identifier for the paper
            metadata: Paper metadata dictionary
            
        Returns:
            True if paper was added successfully
            
        Raises:
            CorpusError: If paper cannot be added
        """
        try:
            # Create paper directory
            paper_dir = Path(self.corpus_dir, "papers", paper_id)
            paper_dir.mkdir(parents=True, exist_ok=True)
            
            # Save metadata
            metadata_file = Path(paper_dir, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            return True
            
        except (OSError, json.JSONEncodeError) as e:
            raise CorpusError(f"Cannot add paper {paper_id}: {e}")

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Get metadata for a paper.
        
        Args:
            paper_id: Unique identifier for the paper
            
        Returns:
            Paper metadata dictionary
            
        Raises:
            CorpusError: If paper not found or metadata cannot be read
        """
        metadata_file = Path(self.corpus_dir, "papers", paper_id, "metadata.json")
        
        if not metadata_file.exists():
            raise CorpusError(f"Paper {paper_id} not found")
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise CorpusError(f"Cannot read metadata for paper {paper_id}: {e}")

    def list_papers(self) -> List[str]:
        """List all papers in the corpus.
        
        Returns:
            List of paper IDs
        """
        papers_dir = Path(self.corpus_dir, "papers")
        
        if not papers_dir.exists():
            return []
        
        return [d.name for d in papers_dir.iterdir() if d.is_dir()]

    def search_papers(self, query: str, field: str = "title") -> List[str]:
        """Search papers in the corpus.
        
        Args:
            query: Search query string
            field: Field to search in (default: "title")
            
        Returns:
            List of paper IDs matching the query
        """
        results = []
        papers = self.list_papers()
        
        for paper_id in papers:
            try:
                metadata = self.get_paper_metadata(paper_id)
                if field in metadata:
                    field_value = str(metadata[field]).lower()
                    if query.lower() in field_value:
                        results.append(paper_id)
            except CorpusError:
                # Skip papers with errors
                continue
        
        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get corpus statistics.
        
        Returns:
            Dictionary with corpus statistics
        """
        papers = self.list_papers()
        
        # Calculate corpus size
        corpus_size_bytes = 0
        for paper_id in papers:
            paper_dir = Path(self.corpus_dir, "papers", paper_id)
            if paper_dir.exists():
                for file_path in paper_dir.rglob("*"):
                    if file_path.is_file():
                        corpus_size_bytes += file_path.stat().st_size
        
        corpus_size_mb = corpus_size_bytes / (1024 * 1024)
        
        return {
            "total_papers": len(papers),
            "corpus_size_mb": round(corpus_size_mb, 4),  # More precision to show small sizes
            "creation_date": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }
