"""UNAM repository implementation (repositorio.unam.mx HTML scraping)."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import (
    handle_from_unam_url,
    sanitize_paper_id,
)
from semantic_corpus.repositories._scraper import RateLimitedSession


class UnamRepository(RepositoryInterface):
    """Adapter applies web scraping to Repositorio Institucional UNAM (repositorio.unam.mx)"""

    def __init__(self) -> None:
        super().__init__()
        self.name = "UNAM"
        self.base_url = "https://repositorio.unam.mx"
        self.search_url = "https://repositorio.unam.mx/contenidos"
        self.http = RateLimitedSession(
            delay_seconds=1.0,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self.http.session.headers.update(
            {
                "Referer": "https://repositorio.unam.mx/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
            }
        )

    def _extract_article_links(self, html: str) -> List[str]:
        """Extracts unique item canonical links from search result HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []

        # Find elements with data-id or cont-text-title-record-min anchors
        for el in soup.select(
            "div.doc-element-grid[data-id], div[data-id], a.cont-text-title-record-min, a[href*='/contenidos/']"
        ):
            data_id = el.get("data-id")
            if data_id and data_id.isdigit():
                canonical_url = f"{self.base_url}/contenidos/{data_id}"
                if canonical_url not in links:
                    links.append(canonical_url)
                continue

            href = el.get("href") or el.get("data-testlink") or ""
            if not href or any(
                p in href
                for p in ["/wp-content", "/normatividad", "?f=", "?c=", "/directorio", "/contacto"]
            ):
                continue

            match = re.search(r"/contenidos/(?:ficha/.*?-)?(\d+)", href)
            if match:
                canonical_url = f"{self.base_url}/contenidos/{match.group(1)}"
                if canonical_url not in links:
                    links.append(canonical_url)
            elif "/contenidos/" in href and not href.rstrip("/").endswith("/contenidos"):
                clean_href = href.split("?")[0].split("#")[0]
                full_url = urljoin(self.base_url, clean_href)
                if full_url not in links:
                    links.append(full_url)

        return links

    def _extract_metadata(self, html: str, article_url: str) -> Dict[str, Any]:
        """Extracts metadata from the item's tags"""
        soup = BeautifulSoup(html, "html.parser")
        paper_id = handle_from_unam_url(article_url)

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
        if not pdf_url:
            pdf_anchor = (
                soup.select_one('a[href$=".pdf"]')
                or soup.select_one('a[href*=".pdf"]')
                or soup.select_one("a.anchore-complete-record[data-url]")
            )
            if pdf_anchor:
                pdf_url = pdf_anchor.get("data-url") or pdf_anchor.get("href", "")

        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = urljoin(self.base_url, pdf_url)

        return {
            "paper_id": paper_id,
            "url": article_url,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": meta("citation_journal_title") or meta("citation_publisher") or "Universidad Nacional Autónoma de México",
            "doi": meta("citation_doi"),
            "publication_date": meta("citation_publication_date") or meta("citation_date"),
            "pdf_url": pdf_url,
            "source_repository": "unam",
        }

    def search_papers(
        self,
        query: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Looks for documents in Repositorio Institucional UNAM and extracts metadata"""
        del start_date, end_date
        clean_query = query.strip('()"\' ')
        params = {"q": clean_query}
        for key, value in kwargs.items():
            if key not in params:
                params[key] = value

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
        """Gets metadata via URL or ID"""
        if paper_id.startswith("http://") or paper_id.startswith("https://"):
            url = paper_id
        elif paper_id.startswith("www."):
            url = f"https://{paper_id}"
        else:
            # Recovers URL using ID (e.g.: unam_45182 -> /contenidos/45182)
            clean = paper_id.replace("unam_", "")
            url = f"{self.base_url}/contenidos/{clean}"

        response = self.http.get(url)
        if not response:
            raise RepositoryError(
                f"Could not find the document in the UNAM repository, id: {paper_id}"
            )
        return self._extract_metadata(response.text, response.url or url)

    def download_paper(
        self,
        paper_id: str,
        output_dir: Path,
        formats: Optional[List[str]] = None,
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
        meta_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        downloaded_files.append(str(meta_path))

        # 2. Downloads PDF, if available
        if "pdf" in formats and metadata.get("pdf_url"):
            pdf_resp = self.http.get(metadata["pdf_url"])
            if pdf_resp and (
                pdf_resp.content.startswith(b"%PDF")
                or "pdf" in pdf_resp.headers.get("content-type", "").lower()
            ):
                pdf_path = output_dir / f"{safe_id}.pdf"
                pdf_path.write_bytes(pdf_resp.content)
                downloaded_files.append(str(pdf_path))

        return {"success": True, "paper_id": safe_id, "files": downloaded_files}

    def get_repository_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "search_url": self.search_url,
            "description": "Repositorio Institucional de la Universidad Nacional Autónoma de México (UNAM)",
            "supported_formats": ["pdf", "metadata"],
            "notes": "Scraping on Repositorio Institucional UNAM (repositorio.unam.mx)",
        }
