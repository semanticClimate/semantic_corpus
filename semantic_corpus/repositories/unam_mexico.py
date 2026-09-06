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
        self.name = "unam_mexico"
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

    def _resolve_external_pdf(self, external_url: str) -> str:
        """Resolves fulltext PDF URL from external journal or OJS page."""
        try:
            resp = self.http.get(external_url, timeout=10)
            if not resp:
                return ""
            sub_soup = BeautifulSoup(resp.text, "html.parser")
            for a in sub_soup.find_all("a"):
                href = a.get("href") or ""
                if "/article/download/" in href or href.lower().endswith(".pdf"):
                    return urljoin(external_url, href)
        except Exception:
            pass
        return ""

    def _extract_metadata(self, html: str, article_url: str) -> Dict[str, Any]:
        """Extracts metadata from the item's tags and MARC21 elements."""
        soup = BeautifulSoup(html, "html.parser")
        paper_id = handle_from_unam_url(article_url)

        # 1. Parse MARC21 tags from <p><strong>tag:</strong> value</p>
        marc: Dict[str, str] = {}
        for p in soup.find_all("p"):
            strong = p.find("strong")
            if strong:
                strong_txt = strong.get_text().strip().rstrip(":")
                if re.match(r"^\d{3}\.", strong_txt) or strong_txt in ("dor_id", "handle"):
                    val = p.get_text().replace(strong.get_text(), "").strip()
                    marc[strong_txt] = val

        def meta(name: str) -> str:
            el = soup.select_one(f'meta[name="{name}"]')
            return el.get("content", "").strip() if el else ""

        # Title: MARC 245.* or meta citation_title or fallback
        title = meta("citation_title")
        if not title:
            for k, v in marc.items():
                if k.startswith("245."):
                    title = v
                    break
        if not title:
            h_title = soup.select_one("h1, h2, .cont-text-title-record-min")
            if h_title and "No entro" not in h_title.get_text():
                title = h_title.get_text(strip=True)
            elif soup.title and "Repositorio Institucional" not in soup.title.get_text():
                title = soup.title.get_text(strip=True)

        # Authors: MARC 100.* and 700.* or meta citation_author
        authors = [
            el.get("content", "").strip()
            for el in soup.select('meta[name="citation_author"]')
            if el.get("content")
        ]
        if not authors:
            for k, v in marc.items():
                if k.startswith("100.") or k.startswith("700."):
                    for author in v.split(";"):
                        author = author.strip()
                        if author and author not in authors:
                            authors.append(author)

        # Abstract: MARC 520.* or meta citation_abstract
        abstract = meta("citation_abstract") or meta("description")
        if not abstract or "El Repositorio Institucional" in abstract:
            for k, v in marc.items():
                if k.startswith("520."):
                    abstract = v
                    break

        # Publication date: MARC 264.*, 260.*, or meta
        pub_date = meta("citation_publication_date") or meta("citation_date")
        if not pub_date:
            for k, v in marc.items():
                if k.startswith("264.") or k.startswith("260."):
                    pub_date = v
                    break

        # Journal / Publisher: MARC 773.* or meta
        journal = meta("citation_journal_title") or meta("citation_publisher")
        if not journal:
            for k, v in marc.items():
                if k.startswith("773."):
                    journal = v
                    break
        if not journal:
            journal = "Universidad Nacional Autónoma de México"

        # DOI
        doi = meta("citation_doi")
        if not doi:
            for k, v in marc.items():
                if "doi" in k.lower() or "10." in v:
                    doi = v
                    break

        # PDF URL
        pdf_url = meta("citation_pdf_url")
        if not pdf_url:
            pdf_anchor = (
                soup.select_one('a[href$=".pdf"]')
                or soup.select_one('a[href*=".pdf"]')
                or soup.select_one("a.anchore-complete-record[data-url]")
            )
            if pdf_anchor:
                pdf_url = pdf_anchor.get("data-url") or pdf_anchor.get("href", "")

        # Check MARC 856.* (Electronic location / fulltext link)
        if not pdf_url:
            for k, v in marc.items():
                if k.startswith("856.") and v.startswith("http"):
                    if ".pdf" in v.lower():
                        pdf_url = v
                    else:
                        pdf_url = self._resolve_external_pdf(v)
                    if pdf_url:
                        break

        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = urljoin(self.base_url, pdf_url)

        return {
            "paper_id": paper_id,
            "url": article_url,
            "title": title or "",
            "abstract": abstract or "",
            "authors": authors,
            "journal": journal,
            "doi": doi or "",
            "publication_date": pub_date or "",
            "pdf_url": pdf_url or "",
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
            match = re.search(r"/contenidos/(\d+)", link)
            target_url = (
                f"{self.base_url}/contenidos/ficha/item-{match.group(1)}"
                if match
                else link
            )
            art_resp = self.http.get(target_url)
            if not art_resp:
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
            # Recovers URL using ID (e.g.: unam_45182 -> /contenidos/ficha/item-45182)
            clean = paper_id.replace("unam_", "")
            url = f"{self.base_url}/contenidos/ficha/item-{clean}"

        response = self.http.get(url)
        if not response and "/ficha/item-" in url:
            clean = paper_id.replace("unam_", "")
            response = self.http.get(f"{self.base_url}/contenidos/{clean}")
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

        # If formats specified (e.g. ["pdf"]), ensure requested format was downloaded
        if formats and "pdf" in formats:
            has_pdf = any(f.endswith(".pdf") for f in downloaded_files)
            if not has_pdf:
                return {
                    "success": False,
                    "paper_id": safe_id,
                    "files": downloaded_files,
                    "error": "No PDF downloaded",
                }

        return {"success": True, "paper_id": safe_id, "files": downloaded_files}

    def get_repository_info(self) -> Dict[str, Any]:
        return {
            "name": "UNAM",
            "base_url": self.base_url,
            "search_url": self.search_url,
            "description": "Repositorio Institucional de la Universidad Nacional Autónoma de México (UNAM)",
            "supported_formats": ["pdf", "metadata"],
            "notes": "Scraping on Repositorio Institucional UNAM (repositorio.unam.mx)",
        }

