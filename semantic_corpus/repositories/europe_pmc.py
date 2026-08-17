"""Europe PMC repository implementation."""

import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional

from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.core.exceptions import RepositoryError


class EuropePMCRepository(RepositoryInterface):
    """Europe PMC repository implementation."""

    def __init__(self) -> None:
        """Initialize Europe PMC repository."""
        super().__init__()
        self.name = "Europe PMC"
        self.base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    def _paper_to_result(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a Europe PMC API paper record."""
        return {
            "pmcid": paper.get("pmcid", ""),
            "pmid": paper.get("pmid", ""),
            "title": paper.get("title", ""),
            "abstract": paper.get("abstractText", ""),
            "authors": paper.get("authorList", {}).get("author", []),
            "publication_date": paper.get("firstPublicationDate", ""),
            "journal": paper.get("journalTitle", ""),
            "doi": paper.get("doi", ""),
            "full_text_urls": paper.get("fullTextUrlList", {}).get("fullTextUrl", []),
            "has_pdf": paper.get("hasPDF", ""),
            "is_open_access": paper.get("isOpenAccess", ""),
        }

    def _search_one_paper(self, paper_id: str) -> Dict[str, Any]:
        """Fetch one Europe PMC record by external ID."""
        query = f"PMCID:{paper_id}" if paper_id.startswith("PMC") else f"EXT_ID:{paper_id}"
        params = {
            "query": query,
            "format": "json",
            "resultType": "core"
        }
        response = requests.get(f"{self.base_url}/search", params=params)
        response.raise_for_status()
        data = response.json()

        if not data.get("resultList", {}).get("result"):
            raise RepositoryError(f"Paper {paper_id} not found")

        return data["resultList"]["result"][0]

    def _find_pdf_url(self, paper: Dict[str, Any], pmcid: str) -> Optional[str]:
        """Return the best open-access PDF URL for a Europe PMC record."""
        full_text_urls = paper.get("fullTextUrlList", {}).get("fullTextUrl", [])
        if isinstance(full_text_urls, dict):
            full_text_urls = [full_text_urls]

        for entry in full_text_urls:
            if (
                entry.get("documentStyle") == "pdf"
                and entry.get("availabilityCode") == "OA"
                and entry.get("url")
            ):
                return entry["url"]

        if pmcid:
            return f"https://europepmc.org/articles/{pmcid}?pdf=render"

        return None

    def search_papers(
        self,
        query: str,
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Search for papers in Europe PMC."""
        try:
            # Build search parameters
            params = {
                "query": query,
                "format": "json",
                "pageSize": min(limit, 1000),  # Europe PMC max is 1000
                "resultType": "core"
            }
            
            # Add date filters if provided
            if start_date and end_date:
                params["query"] = f"({query}) AND (FIRST_PDATE:[{start_date} TO {end_date}])"
            elif end_date:
                params["query"] = f"({query}) AND (FIRST_PDATE:[TO {end_date}])"
            
            # Make API request
            response = requests.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for paper in data.get("resultList", {}).get("result", []):
                results.append(self._paper_to_result(paper))
            
            return results[:limit]
            
        except requests.RequestException as e:
            raise RepositoryError(f"Europe PMC search failed: {e}")

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Get metadata for a specific paper from Europe PMC."""
        try:
            paper = self._search_one_paper(paper_id)
            return self._paper_to_result(paper)
            
        except requests.RequestException as e:
            raise RepositoryError(f"Failed to get metadata for {paper_id}: {e}")

    def download_paper(
        self,
        paper_id: str,
        output_dir: Path,
        formats: List[str] = None
    ) -> Dict[str, Any]:
        """Download a paper from Europe PMC."""
        if formats is None:
            formats = ["xml"]
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            downloaded_files = []
            
            paper = None
            pmcid = paper_id if paper_id.startswith("PMC") else ""

            # Get PMCID for download - if paper_id is PMID, search for PMCID
            if not paper_id.startswith("PMC") and not paper_id.startswith("PPR"):
                paper = self._search_one_paper(paper_id)
                pmcid = paper.get("pmcid", "")
                if not pmcid:
                    raise RepositoryError(f"No PMCID found for {paper_id}")

                # Extract number from PMCID (remove PMC prefix)
                download_id = pmcid.replace("PMC", "")
            else:
                # Use paper_id directly for PMC or PPR IDs, but remove PMC prefix if present
                if paper_id.startswith("PMC"):
                    download_id = paper_id.replace("PMC", "")
                else:
                    download_id = paper_id
            
            for format_type in formats:
                try:
                    if format_type == "xml":
                        xml_url = f"{self.base_url}/PMC{download_id}/fullTextXML"
                        response = requests.get(xml_url)
                        response.raise_for_status()

                        xml_file = output_dir / f"{paper_id}.xml"
                        xml_file.write_bytes(response.content)
                        downloaded_files.append(str(xml_file))

                    elif format_type == "pdf":
                        pdf_url = self._find_pdf_url(paper or {}, pmcid)
                        if not pdf_url:
                            continue

                        response = requests.get(pdf_url)
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "")
                        if (
                            "pdf" not in content_type.lower()
                            and not response.content.startswith(b"%PDF")
                        ):
                            continue

                        pdf_file = output_dir / f"{paper_id}.pdf"
                        pdf_file.write_bytes(response.content)
                        downloaded_files.append(str(pdf_file))
                except requests.RequestException:
                    continue

            if not downloaded_files:
                raise RepositoryError(f"No files downloaded for {paper_id}")

            return {
                "success": True,
                "paper_id": paper_id,
                "files": downloaded_files
            }

        except RepositoryError:
            raise
        except requests.RequestException as e:
            raise RepositoryError(f"Failed to download {paper_id}: {e}")

    def get_repository_info(self) -> Dict[str, Any]:
        """Get information about Europe PMC repository."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "description": "Europe PMC is an open science platform that enables access to a world of biomedical literature",
            "supported_formats": ["xml", "pdf"],
            "max_results_per_query": 1000,
            "api_documentation": "https://europepmc.org/Help"
        }
