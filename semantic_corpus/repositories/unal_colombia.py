"""UNAL (Universidad Nacional de Colombia) repository implementation (DSpace 7 HTML/REST scraping)."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import (
    handle_from_unal_colombia_url,
    sanitize_paper_id,
)
from semantic_corpus.repositories._scraper import RateLimitedSession


class UnalRepository(RepositoryInterface):
    """Adapter applies web scraping and REST discovery to Repositorio Institucional UNAL (Universidad Nacional de Colombia)"""

    def __init__(self) -> None:
        super().__init__()
        self.name = "unal_colombia"
        self.base_url = "https://repositorio.unal.edu.co"
        self.home_url = "https://repositorio.unal.edu.co/home"
        self.search_url = "https://repositorio.unal.edu.co/search"
        self.rest_search_url = "https://repositorio.unal.edu.co/server/api/discover/search/objects"
        self.http = RateLimitedSession(
            delay_seconds=1.0,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self.http.session.headers.update(
            {
                "Referer": "https://repositorio.unal.edu.co/home",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
                "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
            }
        )

    def _extract_article_links(self, html: str) -> List[str]:
        """Extracts unique item links (/handle/ or /items/) from HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []

        # 1. Search for handle anchors
        for anchor in soup.select('a[href*="/handle/"]'):
            href = anchor.get("href", "")
            if not href or any(p in href for p in ["/browse", "/community-list", "/home"]):
                continue
            match = re.search(r'/handle/([\w.]+)/(\w+)', href)
            if match:
                full_url = f"{self.base_url}/handle/{match.group(1)}/{match.group(2)}"
                if full_url not in links:
                    links.append(full_url)

        # 2. Search for DSpace 7 items anchors (/items/<uuid>)
        for anchor in soup.select('a[href*="/items/"]'):
            href = anchor.get("href", "")
            if not href or any(p in href for p in ["/browse", "/community-list", "/home"]):
                continue
            match = re.search(r'/items/([a-f0-9\-]{36})', href, re.IGNORECASE)
            if match:
                full_url = f"{self.base_url}/items/{match.group(1)}"
                if full_url not in links:
                    links.append(full_url)

        return links

    def _extract_metadata(self, html: str, article_url: str) -> Dict[str, Any]:
        """Extracts metadata from the item's tags"""
        soup = BeautifulSoup(html, "html.parser")
        paper_id = handle_from_unal_colombia_url(article_url)

        def meta(name: str) -> str:
            el = soup.select_one(f'meta[name="{name}"]')
            return el.get("content", "").strip() if el else ""

        if meta("citation_abstract_html_url"):
            paper_id = handle_from_unal_colombia_url(meta("citation_abstract_html_url"))

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
                soup.select_one('a[href*="/bitstreams/"]')
                or soup.select_one('a[href*="/bitstream/"]')
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
            "journal": meta("citation_journal_title") or meta("citation_publisher") or "Universidad Nacional de Colombia",
            "doi": meta("citation_doi"),
            "publication_date": meta("citation_publication_date") or meta("citation_date"),
            "pdf_url": pdf_url,
            "source_repository": "unal_colombia",
        }

    def search_papers(
        self,
        query: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Looks for documents in Repositorio UNAL and extracts metadata"""
        del start_date, end_date
        clean_query = query.strip('()"\' ')
        results: List[Dict[str, Any]] = []

        # 1. Try DSpace 7 REST discovery API
        rest_params = {"query": clean_query, "size": min(limit, 20)}
        for k, v in kwargs.items():
            if k not in rest_params:
                rest_params[k] = v

        rest_resp = self.http.get(self.rest_search_url, params=rest_params)
        if rest_resp and ("application/json" in rest_resp.headers.get("content-type", "") or rest_resp.text.strip().startswith("{")):
            try:
                data = json.loads(rest_resp.text)
                objects = (
                    data.get("_embedded", {})
                    .get("searchResult", {})
                    .get("_embedded", {})
                    .get("objects", [])
                )
                for obj in objects:
                    idx_obj = obj.get("_embedded", {}).get("indexableObject", {})
                    item_handle = idx_obj.get("handle")
                    item_id = idx_obj.get("id")
                    item_url = None
                    if item_handle:
                        item_url = f"{self.base_url}/handle/{item_handle}"
                    elif item_id:
                        item_url = f"{self.base_url}/items/{item_id}"

                    if not item_url:
                        continue

                    # Extract metadata from REST response if available
                    meta_dict = idx_obj.get("metadata", {})
                    if meta_dict:
                        title_vals = meta_dict.get("dc.title", [])
                        title = title_vals[0].get("value") if title_vals else ""
                        authors = [
                            a.get("value")
                            for a in meta_dict.get("dc.contributor.author", [])
                            if a.get("value")
                        ]
                        abstract_vals = meta_dict.get("dc.description.abstract", [])
                        abstract = abstract_vals[0].get("value") if abstract_vals else ""
                        date_vals = meta_dict.get("dc.date.issued", [])
                        pub_date = date_vals[0].get("value") if date_vals else ""
                        doi_vals = meta_dict.get("dc.identifier.doi", [])
                        doi = doi_vals[0].get("value") if doi_vals else ""

                        results.append({
                            "paper_id": handle_from_unal_colombia_url(item_url),
                            "url": item_url,
                            "title": title,
                            "abstract": abstract,
                            "authors": authors,
                            "journal": "Universidad Nacional de Colombia",
                            "doi": doi,
                            "publication_date": pub_date,
                            "pdf_url": None,
                            "source_repository": "unal_colombia",
                        })
                    else:
                        # Fetch HTML for this item
                        art_resp = self.http.get(item_url)
                        if art_resp:
                            results.append(self._extract_metadata(art_resp.text, item_url))

                    if len(results) >= limit:
                        return results
            except Exception:
                pass

        if results:
            return results

        # 2. HTML search fallback
        html_params = {"query": clean_query, "spc.rpp": min(limit, 20)}
        for k, v in kwargs.items():
            if k not in html_params:
                html_params[k] = v

        response = self.http.get(self.search_url, params=html_params)
        if not response:
            fallback_url = f"{self.base_url}/discover"
            response = self.http.get(fallback_url, params=html_params)
            if not response:
                response = self.http.get(self.home_url, params=html_params)

        if not response:
            raise RepositoryError(f"Error occurred while looking for: {query}")

        links = self._extract_article_links(response.text)[:limit]
        for link in links:
            art_resp = self.http.get(link)
            if not art_resp:
                continue
            results.append(self._extract_metadata(art_resp.text, link))
            if len(results) >= limit:
                break
        return results

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Gets metadata via URL, UUID, or Handle"""
        if paper_id.startswith("http://") or paper_id.startswith("https://"):
            url = paper_id
        elif paper_id.startswith("www."):
            url = f"https://{paper_id}"
        else:
            clean = paper_id.replace("unal_colombia_", "").replace("unal_", "")
            # Check for UUID (e.g. 44fc646d-bbad-4be9-b008-0147830d0039 or with _)
            if re.match(r"^[a-f0-9]{8}[-_][a-f0-9]{4}[-_][a-f0-9]{4}[-_][a-f0-9]{4}[-_][a-f0-9]{12}$", clean, re.I):
                uuid_str = clean.replace("_", "-")
                url = f"{self.base_url}/items/{uuid_str}"
            elif clean.isdigit():
                url = f"{self.base_url}/handle/unal/{clean}"
            elif "/" in clean or "_" in clean:
                clean_handle = clean.replace("_", "/")
                url = f"{self.base_url}/handle/{clean_handle}"
            else:
                url = f"{self.base_url}/handle/unal/{clean}"

        response = self.http.get(url)
        if not response:
            raise RepositoryError(
                f"Could not find the document in the UNAL repository, id: {paper_id}"
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
            "description": "Repositorio Institucional de la Universidad Nacional de Colombia",
            "supported_formats": ["pdf", "metadata"],
            "notes": "Scraping and DSpace 7 REST on Repositorio Institucional UNAL (repositorio.unal.edu.co)",
        }
