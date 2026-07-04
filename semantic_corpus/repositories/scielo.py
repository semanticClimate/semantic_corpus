"""SciELO repository implementation (search.scielo.org scraping)."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import pid_from_scielo_url, sanitize_paper_id
from semantic_corpus.repositories._scraper import RateLimitedSession


class SciELORepository(RepositoryInterface):
    """SciELO adapter using the public search portal and article pages."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "SciELO"
        self.base_url = "https://www.scielo.org"
        self.search_url = "https://search.scielo.org/"
        self.http = RateLimitedSession(delay_seconds=1.5)

    def _extract_article_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []
        for anchor in soup.select('a[href*="script=sci_arttext"]'):
            href = anchor.get("href")
            if not href:
                continue
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = urljoin(self.search_url, href)
            elif not href.startswith("http"):
                href = urljoin(self.search_url, href)
            if href not in links:
                links.append(href)
        return links

    def _extract_metadata(self, html: str, article_url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        pid = pid_from_scielo_url(article_url)
        paper_id = sanitize_paper_id(pid or article_url)

        title = ""
        for selector in ("h1.title", ".title", "h1", "meta[name='citation_title']"):
            element = soup.select_one(selector)
            if not element:
                continue
            title = element.get("content") if element.name == "meta" else element.get_text(strip=True)
            if title:
                break

        authors: List[str] = []
        for selector in (".authors", ".author", "meta[name='citation_author']"):
            for element in soup.select(selector):
                if element.name == "meta":
                    name = element.get("content", "")
                else:
                    name = element.get_text(strip=True)
                if name and name not in authors:
                    authors.append(name)

        abstract = ""
        for selector in (".abstract", ".resumo", "meta[name='citation_abstract']"):
            element = soup.select_one(selector)
            if not element:
                continue
            abstract = element.get("content") if element.name == "meta" else element.get_text(strip=True)
            if abstract:
                break

        journal = ""
        journal_elem = soup.select_one("meta[name='citation_journal_title']")
        if journal_elem:
            journal = journal_elem.get("content", "")

        doi = ""
        doi_elem = soup.select_one("meta[name='citation_doi']")
        if doi_elem:
            doi = doi_elem.get("content", "")

        pdf_urls: List[str] = []
        for selector in (
            'a[href*="script=sci_pdf"]',
            'a[href*=".pdf"]',
            'meta[name="citation_pdf_url"]',
        ):
            for element in soup.select(selector):
                href = element.get("href") or element.get("content")
                if href:
                    if not href.startswith("http"):
                        parsed = urlparse(article_url)
                        href = f"{parsed.scheme}://{parsed.netloc}{href}"
                    if href not in pdf_urls:
                        pdf_urls.append(href)

        return {
            "paper_id": paper_id,
            "pid": pid,
            "url": article_url,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal,
            "doi": doi,
            "pdf_urls": pdf_urls,
            "source_repository": "scielo",
        }

    def search_papers(
        self,
        query: str,
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Search SciELO and fetch metadata for matched articles."""
        del start_date, end_date  # SciELO search portal has no stable date filter API.

        params = {
            "q": query,
            "count": min(limit, 20),
            "from": 0,
            "output": "site",
            "format": "summary",
        }
        response = self.http.get(self.search_url, params=params)
        if not response:
            raise RepositoryError("SciELO search request failed")

        article_links = self._extract_article_links(response.text)[:limit]
        results: List[Dict[str, Any]] = []
        for link in article_links:
            article_response = self.http.get(link)
            if not article_response:
                continue
            results.append(self._extract_metadata(article_response.text, link))
            if len(results) >= limit:
                break
        return results

    def _article_urls_for_pid(self, pid: str) -> List[str]:
        """Return likely SciELO article URLs for a pid across regional mirrors."""
        mirrors = (
            "www.scielo.br",
            "ve.scielo.org",
            "www.scielo.cl",
            "www.scielo.org.mx",
            "www.scielo.sa.cr",
        )
        return [
            f"https://{host}/scielo.php?script=sci_arttext&pid={pid}&lng=en"
            for host in mirrors
        ]

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Fetch SciELO metadata by pid or article URL."""
        if paper_id.startswith("http"):
            candidates = [paper_id]
        else:
            candidates = self._article_urls_for_pid(paper_id)

        for url in candidates:
            response = self.http.get(url)
            if response:
                return self._extract_metadata(response.text, response.url)

        raise RepositoryError(f"SciELO article not found: {paper_id}")

    def download_paper(
        self,
        paper_id: str,
        output_dir: Path,
        formats: List[str] = None,
    ) -> Dict[str, Any]:
        """Download SciELO HTML and optional PDF."""
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

        if "pdf" in formats:
            for pdf_url in metadata.get("pdf_urls") or []:
                pdf_response = self.http.get(pdf_url)
                if not pdf_response:
                    continue
                content_type = pdf_response.headers.get("content-type", "")
                if pdf_response.content.startswith(b"%PDF") or "pdf" in content_type.lower():
                    pdf_path = output_dir / f"{safe_id}.pdf"
                    pdf_path.write_bytes(pdf_response.content)
                    downloaded_files.append(str(pdf_path))
                    break

        if not downloaded_files:
            raise RepositoryError(f"No files downloaded for {paper_id}")

        return {"success": True, "paper_id": safe_id, "files": downloaded_files}

    def get_repository_info(self) -> Dict[str, Any]:
        """Return SciELO repository metadata."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "description": (
                "SciELO is a multilingual open-access repository focused on "
                "Latin America, Spain, Portugal, and South Africa"
            ),
            "supported_formats": ["html", "pdf", "metadata"],
            "max_results_per_query": 20,
            "api_documentation": "https://search.scielo.org/",
            "notes": "Uses search.scielo.org HTML scraping; no public REST API.",
        }
