"""Kerwa (Universidad de Costa Rica) repository implementation (DSpace HTML scraping)."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import (
    handle_from_kerwa_url,
    sanitize_paper_id,
)
from semantic_corpus.repositories._scraper import RateLimitedSession


class KerwaRepository(RepositoryInterface):
    """Adapter applies web scraping to Repositorio Institucional Kérwá (Universidad de Costa Rica)"""

    def __init__(self) -> None:
        super().__init__()
        self.name = "Kerwa"
        self.base_url = "https://www.kerwa.ucr.ac.cr"
        self.home_url = "https://www.kerwa.ucr.ac.cr/home"
        self.search_url = "https://www.kerwa.ucr.ac.cr/discover"
        self.http = RateLimitedSession(
            delay_seconds=1.0,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self.http.session.headers.update(
            {
                "Referer": "https://www.kerwa.ucr.ac.cr/home",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-CR,es;q=0.9,en;q=0.8",
            }
        )

    def _extract_article_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []
        for anchor in soup.select('a[href*="/handle/"]'):
            href = anchor.get("href", "")
            if not href or any(p in href for p in ["/browse", "/community-list", "/home"]):
                continue
            match = re.search(r'/handle/(\d+(?:\.\d+)?)/(\d+)', href)
            if match:
                full_url = f"{self.base_url}/handle/{match.group(1)}/{match.group(2)}"
                if full_url not in links:
                    links.append(full_url)
        return links

    def _extract_metadata(self, html: str, article_url: str) -> Dict[str, Any]:
        """Extracts metadata from the item's tags"""
        soup = BeautifulSoup(html, "html.parser")
        paper_id = handle_from_kerwa_url(article_url)

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
                soup.select_one('a[href*="/bitstream/"][href$=".pdf"]')
                or soup.select_one('a[href*="/bitstream/"]')
                or soup.select_one("a.view-open a")
                or soup.select_one("a.view-open")
                or soup.select_one('a[href$=".pdf"]')
            )
            if pdf_anchor and pdf_anchor.get("href"):
                pdf_url = pdf_anchor.get("href", "")

        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = urljoin(self.base_url, pdf_url)

        return {
            "paper_id": paper_id,
            "url": article_url,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": meta("citation_journal_title") or meta("citation_publisher") or "Universidad de Costa Rica",
            "doi": meta("citation_doi"),
            "publication_date": meta("citation_publication_date") or meta("citation_date"),
            "pdf_url": pdf_url,
            "source_repository": "kerwa",
        }

    def search_papers(
        self,
        query: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Looks for documents in Repositorio Kérwá and extracts metadata"""
        del start_date, end_date
        clean_query = query.strip('()"\' ')
        params = {"query": clean_query, "rpp": min(limit, 20)}
        for key, value in kwargs.items():
            if key not in params:
                params[key] = value

        response = self.http.get(self.search_url, params=params)
        if not response:
            fallback_url = f"{self.base_url}/simple-search"
            response = self.http.get(fallback_url, params=params)
            if not response:
                response = self.http.get(self.home_url, params=params)

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
        if paper_id.startswith("http://") or paper_id.startswith("https://"):
            url = paper_id
        elif paper_id.startswith("www."):
            url = f"https://{paper_id}"
        else:
            # Recovers URL using ID (e.g.: kerwa_10669_12345 -> /handle/10669/12345)
            clean = paper_id.replace("kerwa_", "")
            if clean.isdigit():
                clean_handle = f"10669/{clean}"
            else:
                clean_handle = clean.replace("_", "/")
            url = f"{self.base_url}/handle/{clean_handle}"

        response = self.http.get(url)
        if not response:
            raise RepositoryError(
                f"Could not find the document in the Universidad de Costa Rica repository, id: {paper_id}"
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
            "home_url": self.home_url,
            "description": "Repositorio Institucional Kérwá de la Universidad de Costa Rica",
            "supported_formats": ["pdf", "metadata"],
            "notes": "Scraping on DSpace Kérwá platform (Universidad de Costa Rica)",
        }
