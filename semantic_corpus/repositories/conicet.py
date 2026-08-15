"""RI CONICET repository implementation (DSpace HTML scraping)."""

#RateLimitedSession is in charge of making safe HTTP requests and pauses
#BeautifulSoup extracts links and tags such as <meta>

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import handle_from_conicet_url, sanitize_paper_id
from semantic_corpus.repositories._scraper import RateLimitedSession


class CONICETRepository(RepositoryInterface):
    """Adapter applies web scraping to RI CONICET Digital"""

    def __init__(self) -> None:
        super().__init__()
        self.name = "CONICET"
        self.base_url = "https://ri.conicet.gov.ar"
        self.search_url = "https://ri.conicet.gov.ar/discover"
        self.http = RateLimitedSession(delay_seconds=1.0)

    def _extract_article_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []
        for anchor in soup.select('a[href*="/handle/11336/"]'):
            href = anchor.get("href", "")
            if not href:
                continue
            full_url = urljoin(self.base_url, href)
            if full_url not in links:
                links.append(full_url)
        return links

    def _extract_metadata(self, html: str, article_url: str) -> Dict[str, Any]:
        """Extracts metadata from the item's tags"""
        soup = BeautifulSoup(html, "html.parser")
        paper_id = handle_from_conicet_url(article_url)

        def meta(name: str) -> str:
            el = soup.select_one(f'meta[name="{name}"]')
            return el.get("content", "").strip() if el else ""

        title = meta("citation_title") or (soup.title.get_text(strip=True) if soup.title else "")
        authors = [
            el.get("content", "").strip()
            for el in soup.select('meta[name="citation_author"]')
            if el.get("content")
        ]
        abstract = meta("citation_abstract") or meta("description")
        pdf_url = meta("citation_pdf_url")
        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = urljoin(self.base_url, pdf_url)

        return {
            "paper_id": paper_id,
            "url": article_url,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": meta("citation_journal_title") or meta("citation_publisher"),
            "doi": meta("citation_doi"),
            "publication_date": meta("citation_publication_date") or meta("citation_date"),
            "pdf_url": pdf_url,
            "source_repository": "conicet",
        }

    def search_papers(
            self,
            query: str,
            limit: int = 10,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Looks for docuemnts in RI CONICET and extracts metadata"""
        del start_date, end_date
        params = {"query": query, "rpp": min(limit, 20)}
        response = self.http.get(self.search_url, params=params)
        if not response:
            raise RepositoryError(f"Error occurred while looking for: {query}")

        links = self._extract_article_links(response.text)[:limit]
        results: List[Dict[str, Any]] = []
        for link in links:
            art_resp = self.http.get(link)
            if not art_resp:
                continue
            results.append(self._extract_metadata(art_resp.text, link))
            if len(results) >= limit:
                break
        return results

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Gets metadata via URL or Handle"""
        if paper_id.startswith("http"):
            url = paper_id
        else:
            # Recovers URL using ID (e.g.: conicet_11336_12345 -> /handle/11336/12345)
            clean_handle = paper_id.replace("conicet_", "").replace("_", "/")
            url = f"{self.base_url}/handle/{clean_handle}"

        response = self.http.get(url)
        if not response:
            raise RepositoryError(f"Could not find the document in the CONICET repository, id: {paper_id}")
        return self._extract_metadata(response.text, response.url)

    def download_paper(
            self,
            paper_id: str,
            output_dir: Path,
            formats: List[str] = None,
    ) -> Dict[str, Any]:
        """Downloads PDF and stores metadata as JSON"""
        if formats is None:
            formats = ["pdf"]

        metadata = self.get_paper_metadata(paper_id)
        safe_id = sanitize_paper_id(metadata["paper_id"])
        output_dir.mkdir(parents=True, exist_ok=True)
        downloaded_files: List[str] = []

        # 1. Stores metadata.json
        meta_path = output_dir / f"{safe_id}_metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        downloaded_files.append(str(meta_path))

        # 2. Downloads PDF, if available
        if "pdf" in formats and metadata.get("pdf_url"):
            pdf_resp = self.http.get(metadata["pdf_url"])
            if pdf_resp and (
                    pdf_resp.content.startswith(b"%PDF") or "pdf" in pdf_resp.headers.get("content-type", "").lower()):
                pdf_path = output_dir / f"{safe_id}.pdf"
                pdf_path.write_bytes(pdf_resp.content)
                downloaded_files.append(str(pdf_path))

        return {"success": True, "paper_id": safe_id, "files": downloaded_files}

    def get_repository_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "description": "Repositorio Institucional del CONICET (Argentina)",
            "supported_formats": ["pdf", "metadata"],
            "notes": "Scraping on DSpace CONICET Digital platform",
        }