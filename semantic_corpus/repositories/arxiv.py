"""arXiv repository implementation."""

import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional

from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.core.exceptions import RepositoryError


class ArxivRepository(RepositoryInterface):
    """arXiv repository implementation."""

    def __init__(self) -> None:
        """Initialize arXiv repository."""
        super().__init__()
        self.name = "arXiv"
        self.base_url = "http://export.arxiv.org/api/query"

    def search_papers(
        self,
        query: str,
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        categories: Optional[List[str]] = None,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Search for papers in arXiv."""
        try:
            # Build search parameters
            params = {
                "search_query": query,
                "start": 0,
                "max_results": min(limit, 2000),  # arXiv max is 2000
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            
            # Add category filter if provided
            if categories:
                category_query = " OR ".join([f"cat:{cat}" for cat in categories])
                params["search_query"] = f"({query}) AND ({category_query})"
            
            # Make API request
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            # Parse XML response (arXiv returns XML, not JSON)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            results = []
            for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                # Extract arXiv ID
                arxiv_id = entry.find("{http://www.w3.org/2005/Atom}id").text
                arxiv_id = arxiv_id.split("/")[-1]  # Extract ID from URL
                
                # Extract title
                title = entry.find("{http://www.w3.org/2005/Atom}title").text
                
                # Extract abstract
                abstract = entry.find("{http://www.w3.org/2005/Atom}summary").text
                
                # Extract authors
                authors = []
                for author in entry.findall("{http://www.w3.org/2005/Atom}author"):
                    name = author.find("{http://www.w3.org/2005/Atom}name").text
                    authors.append({"name": name})
                
                # Extract publication date
                published = entry.find("{http://www.w3.org/2005/Atom}published").text
                
                # Extract categories
                categories_list = []
                for category in entry.findall("{http://arxiv.org/schemas/atom}primary_category"):
                    categories_list.append(category.get("term"))
                
                results.append({
                    "arxiv_id": arxiv_id,
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "publication_date": published,
                    "categories": categories_list,
                })
            
            return results[:limit]
            
        except (requests.RequestException, ET.ParseError) as e:
            raise RepositoryError(f"arXiv search failed: {e}")

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Get metadata for a specific paper from arXiv."""
        try:
            # arXiv API expects ID in format: 1234.5678 or cs/1234567
            params = {
                "id_list": paper_id,
                "max_results": 1
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            # Parse XML response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            entry = root.find("{http://www.w3.org/2005/Atom}entry")
            if entry is None:
                raise RepositoryError(f"Paper {paper_id} not found")
            
            # Extract metadata (same as in search_papers)
            arxiv_id = entry.find("{http://www.w3.org/2005/Atom}id").text
            arxiv_id = arxiv_id.split("/")[-1]
            
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            abstract = entry.find("{http://www.w3.org/2005/Atom}summary").text
            
            authors = []
            for author in entry.findall("{http://www.w3.org/2005/Atom}author"):
                name = author.find("{http://www.w3.org/2005/Atom}name").text
                authors.append({"name": name})
            
            published = entry.find("{http://www.w3.org/2005/Atom}published").text
            
            categories_list = []
            for category in entry.findall("{http://arxiv.org/schemas/atom}primary_category"):
                categories_list.append(category.get("term"))
            
            return {
                "arxiv_id": arxiv_id,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "publication_date": published,
                "categories": categories_list,
            }
            
        except (requests.RequestException, ET.ParseError) as e:
            raise RepositoryError(f"Failed to get metadata for {paper_id}: {e}")

    def download_paper(
        self,
        paper_id: str,
        output_dir: Path,
        formats: List[str] = None
    ) -> Dict[str, Any]:
        """Download a paper from arXiv."""
        if formats is None:
            formats = ["pdf"]
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            downloaded_files = []
            
            for format_type in formats:
                if format_type == "pdf":
                    # Download PDF
                    pdf_url = f"http://arxiv.org/pdf/{paper_id}.pdf"
                    response = requests.get(pdf_url)
                    response.raise_for_status()
                    
                    pdf_file = output_dir / f"{paper_id}.pdf"
                    pdf_file.write_bytes(response.content)
                    downloaded_files.append(str(pdf_file))
                
                elif format_type == "source":
                    # Download source (LaTeX)
                    source_url = f"http://arxiv.org/src/{paper_id}"
                    response = requests.get(source_url)
                    response.raise_for_status()
                    
                    source_file = output_dir / f"{paper_id}.tar.gz"
                    source_file.write_bytes(response.content)
                    downloaded_files.append(str(source_file))
            
            return {
                "success": True,
                "paper_id": paper_id,
                "files": downloaded_files
            }
            
        except requests.RequestException as e:
            raise RepositoryError(f"Failed to download {paper_id}: {e}")

    def get_repository_info(self) -> Dict[str, Any]:
        """Get information about arXiv repository."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "description": "arXiv is a free distribution service and an open-access archive for scholarly articles",
            "supported_formats": ["pdf", "source"],
            "max_results_per_query": 2000,
            "api_documentation": "https://arxiv.org/help/api"
        }
