"""Redalyc repository implementation (HTML scraping)."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import id_from_redalyc_url, sanitize_paper_id
from semantic_corpus.repositories._scraper import RateLimitedSession


class RedalycRepository(RepositoryInterface):
    """Redalyc adapter using article pages and homepage discovery."""

    LEGACY_SEARCH_URL = "https://www.redalyc.org/redalyc/search"

    def __init__(self) -> None:
        super().__init__()
        self.name = "Redalyc"
        self.base_url = "https://www.redalyc.org"
        self.http = RateLimitedSession(delay_seconds=1.0)

    def _extract_article_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []
        selectors = (
            'a[href*="articulo.oa"]',
            'a[href*="/articulo"]',
            'a[href*="/article"]',
        )
        for selector in selectors:
            for anchor in soup.select(selector):
                href = anchor.get("href")
                if not href:
                    continue
                full_url = urljoin(self.base_url, href)
                if full_url not in links:
                    links.append(full_url)
        return links

    def _extract_metadata(self, html: str, article_url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        article_id = id_from_redalyc_url(article_url)
        paper_id = sanitize_paper_id(article_id)

        def meta(name: str) -> str:
            element = soup.select_one(f'meta[name="{name}"]')
            return element.get("content", "") if element else ""

        title = meta("citation_title")
        if not title and soup.title:
            title = soup.title.get_text(strip=True)

        authors = [
            element.get("content", "")
            for element in soup.select('meta[name="citation_author"]')
            if element.get("content")
        ]

        pdf_url = meta("citation_pdf_url")
        xml_url = meta("citation_fulltext_html_url")

        return {
            "paper_id": paper_id,
            "redalyc_id": article_id,
            "url": article_url,
            "title": title,
            "abstract": meta("citation_abstract"),
            "authors": authors,
            "journal": meta("citation_journal_title"),
            "doi": meta("citation_doi"),
            "publication_date": meta("citation_publication_date"),
            "pdf_url": pdf_url,
            "xml_url": xml_url,
            "source_repository": "redalyc",
        }

    def _query_matches(self, metadata: Dict[str, Any], query: str) -> bool:
        terms = [term for term in re.split(r"\s+", query.lower()) if term]
        if not terms:
            return True
        haystack = " ".join(
            [
                metadata.get("title") or "",
                metadata.get("abstract") or "",
                metadata.get("journal") or "",
            ]
        ).lower()
        return any(term in haystack for term in terms)

    def _discover_article_links(self, query: str, limit: int) -> List[str]:
        """Try legacy search, then homepage discovery with query filtering."""
        response = self.http.get(
            self.LEGACY_SEARCH_URL,
            params={"q": query, "t": "Art", "limit": str(limit)},
        )
        if response:
            links = self._extract_article_links(response.text)
            if links:
                return links[:limit]

        homepage = self.http.get(self.base_url)
        if not homepage:
            return []

        candidates = self._extract_article_links(homepage.text)
        matched: List[str] = []
        for link in candidates:
            article_response = self.http.get(link)
            if not article_response:
                continue
            metadata = self._extract_metadata(article_response.text, link)
            if self._query_matches(metadata, query):
                matched.append(link)
            if len(matched) >= limit:
                break
        return matched

    def search_papers(
        self,
        query: str,
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Search Redalyc and return article metadata."""
        del start_date, end_date

        article_links = self._discover_article_links(query, min(limit, 20))
        results: List[Dict[str, Any]] = []
        for link in article_links:
            response = self.http.get(link)
            if not response:
                continue
            results.append(self._extract_metadata(response.text, link))
            if len(results) >= limit:
                break
        return results

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Fetch Redalyc metadata by article id or URL."""
        if paper_id.startswith("http"):
            url = paper_id
        else:
            url = f"{self.base_url}/articulo.oa?id={paper_id}"
        response = self.http.get(url)
        if not response:
            raise RepositoryError(f"Redalyc article not found: {paper_id}")
        return self._extract_metadata(response.text, response.url)

    def download_paper(
        self,
        paper_id: str,
        output_dir: Path,
        formats: List[str] = None,
    ) -> Dict[str, Any]:
        """Download Redalyc HTML, metadata, and optional PDF."""
        if formats is None:
            formats = ["html", "pdf"]

        metadata = self.get_paper_metadata(paper_id)
        safe_id = sanitize_paper_id(metadata["paper_id"])
        output_dir.mkdir(parents=True, exist_ok=True)
        downloaded_files: List[str] = []

        if "html" in formats:
            response = self.http.get(metadata["url"])
            if response:
                html_path = output_dir / f"{safe_id}.html"
                html_path.write_text(response.text, encoding="utf-8")
                downloaded_files.append(str(html_path))

        metadata_path = output_dir / f"{safe_id}_metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        downloaded_files.append(str(metadata_path))

        if "pdf" in formats and metadata.get("pdf_url"):
            pdf_response = self.http.get(metadata["pdf_url"])
            if pdf_response and (
                pdf_response.content.startswith(b"%PDF")
                or "pdf" in pdf_response.headers.get("content-type", "").lower()
            ):
                pdf_path = output_dir / f"{safe_id}.pdf"
                pdf_path.write_bytes(pdf_response.content)
                downloaded_files.append(str(pdf_path))

        if not downloaded_files:
            raise RepositoryError(f"No files downloaded for {paper_id}")

        return {"success": True, "paper_id": safe_id, "files": downloaded_files}

    def get_repository_info(self) -> Dict[str, Any]:
        """Return Redalyc repository metadata."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "description": (
                "Redalyc is a multilingual open-access repository focused on "
                "Latin America, Spain, and Portugal"
            ),
            "supported_formats": ["html", "pdf", "metadata"],
            "max_results_per_query": 20,
            "api_documentation": "https://www.redalyc.org/",
            "notes": (
                "Redalyc has no stable public search API; search falls back to "
                "homepage discovery when the legacy endpoint is unavailable."
            ),
        }
