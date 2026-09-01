"""USP repository implementation (repositorio.usp.br HTML scraping)."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import id_from_usp_url, sanitize_paper_id
from semantic_corpus.repositories._scraper import RateLimitedSession

logger = logging.getLogger(__name__)


class UspRepository(RepositoryInterface):
    """Adapter for Universidade de São Paulo (USP) Intellectual Production Repository."""

    def __init__(self) -> None:
        super().__init__()
        self.name = "USP"
        self.base_url = "https://repositorio.usp.br"
        self.search_url = "https://repositorio.usp.br/result.php"
        self.http = RateLimitedSession(
            delay_seconds=0.5,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) "
                "Gecko/20100101 Firefox/120.0"
            ),
        )
        self.http.session.headers.update(
            {
                "Referer": "https://repositorio.usp.br/index.php",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )

    def _extract_article_links(self, html: str) -> List[str]:
        """Extracts unique item links from search result HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []

        # Find anchors pointing to item/<id>
        for anchor in soup.select('article a[href*="item/"], a.uk-link-reset[href*="item/"], a[href*="/item/"]'):
            href = anchor.get("href", "").strip()
            if not href:
                continue
            full_url = urljoin(self.base_url, href)
            if full_url not in links:
                links.append(full_url)

        return links

    def _is_valid_paper(self, metadata: Dict[str, Any], soup: BeautifulSoup) -> bool:
        """Validates that extracted record represents a legitimate paper/thesis."""
        del soup
        title = metadata.get("title", "").strip()
        if not title:
            return False
        return True

    def _extract_metadata(self, html: str, article_url: str) -> Dict[str, Any]:
        """Extracts metadata fields from an item page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        paper_id = id_from_usp_url(article_url)

        def meta(name: str) -> str:
            el = (
                soup.select_one(f'meta[name="{name}"]')
                or soup.select_one(f'meta[name="DC.{name}"]')
                or soup.select_one(f'meta[name="DCTERMS.{name}"]')
                or soup.select_one(f'meta[property="{name}"]')
            )
            return el.get("content", "").strip() if el else ""

        # Title
        title = (
            meta("citation_title")
            or meta("title")
            or meta("DC.title")
        )
        if not title:
            title_el = soup.select_one("p.uk-text-lead, .title-link a, h1, h2")
            if title_el:
                title = title_el.get_text(strip=True)
            elif soup.title:
                title = soup.title.get_text(strip=True)
                if "Detalhe do registro:" in title:
                    title = title.split("Detalhe do registro:", 1)[-1].strip()

        # Authors
        raw_authors = [
            el.get("content", "").strip()
            for el in (
                soup.select('meta[name="citation_author"]')
                + soup.select('meta[name="DC.creator"]')
                + soup.select('meta[name="author"]')
            )
            if el.get("content") and el.get("content").strip()
        ]
        if not raw_authors:
            for a in soup.select('p.uk-article-meta a.link, a[href*="author.person.name"]'):
                name = a.get_text(strip=True)
                if name and name not in raw_authors:
                    raw_authors.append(name)
        authors = list(dict.fromkeys(raw_authors))

        # Abstract
        abstract = (
            meta("citation_abstract")
            or meta("abstract")
            or meta("description")
        )
        if not abstract:
            for el in soup.select(".resumo, .abstract, div[class*='abstract'], div[class*='resumo']"):
                txt = el.get_text(strip=True)
                if txt:
                    abstract = txt
                    break

        # PDF URL
        pdf_url = meta("citation_pdf_url")
        if not pdf_url:
            pdf_anchor = (
                soup.select_one('a[href$=".pdf"]')
                or soup.select_one('a[href*=".pdf"]')
                or soup.select_one('a[title*="PDF"]')
                or soup.select_one('a:-soup-contains("PDF")')
            )
            if pdf_anchor and pdf_anchor.get("href"):
                pdf_url = pdf_anchor.get("href", "")

        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = urljoin(self.base_url, pdf_url)

        # DOI
        doi = meta("citation_doi") or meta("doi")
        if not doi:
            doi_link = soup.select_one('a[href*="doi.org/"]')
            if doi_link and doi_link.get("href"):
                doi = doi_link.get("href", "").split("doi.org/")[-1].strip()

        # Publication date
        pub_date = (
            meta("citation_publication_date")
            or meta("citation_date")
            or meta("date")
            or meta("created")
        )

        # Journal / Publisher
        journal = (
            meta("citation_journal_title")
            or meta("citation_dissertation_institution")
            or meta("citation_publisher")
            or meta("publisher")
            or "Universidade de São Paulo (USP)"
        )

        # Faculty / School / Unidade
        unidade_el = soup.select_one('a[href*="unidadeUSP:"]')
        faculty = unidade_el.get_text(strip=True) if unidade_el else ""

        return {
            "paper_id": paper_id,
            "url": article_url,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal,
            "doi": doi,
            "publication_date": pub_date,
            "pdf_url": pdf_url,
            "source_repository": "usp",
            "faculty": faculty,
        }

    def search_papers(
        self,
        query: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Search papers in the USP repository and extract metadata."""
        del start_date, end_date
        clean_query = query.strip('()"\' ')

        params: Dict[str, Any] = {"search[]": clean_query}

        # Handle optional filters (unit/faculty, source/base)
        faculty_filter = kwargs.get("faculty") or kwargs.get("unidade") or kwargs.get("unit")
        if faculty_filter:
            params["filter[]"] = f'unidadeUSP:"{faculty_filter}"'

        base_filter = kwargs.get("base") or kwargs.get("source")
        if base_filter:
            if "tes" in str(base_filter).lower():
                params["filter[]"] = 'base:"Teses e dissertações"'
            elif "cien" in str(base_filter).lower():
                params["filter[]"] = 'base:"Produção científica"'

        custom_filter = kwargs.get("filter")
        if custom_filter:
            params["filter[]"] = custom_filter

        try:
            response = self.http.get(self.search_url, params=params)
            if not response:
                return []
            links = self._extract_article_links(response.text)
        except Exception as e:
            logger.warning(f"Error querying USP repository for '{query}': {e}")
            return []

        results: List[Dict[str, Any]] = []
        for link in links:
            if len(results) >= limit:
                break
            try:
                art_resp = self.http.get(link)
                if not art_resp:
                    continue
                soup = BeautifulSoup(art_resp.text, "html.parser")
                metadata = self._extract_metadata(art_resp.text, link)
                if self._is_valid_paper(metadata, soup):
                    results.append(metadata)
            except Exception as e:
                logger.warning(f"Error processing document {link}: {e}")
                continue

        return results[:limit]

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Fetch metadata for a paper given its ID or URL."""
        if paper_id.startswith("http"):
            url = paper_id
        else:
            clean_id = paper_id.replace("usp_", "")
            url = f"{self.base_url}/item/{clean_id}"

        response = self.http.get(url)
        if not response:
            raise RepositoryError(
                f"No se pudo encontrar el documento en el repositorio USP, id: {paper_id}"
            )
        return self._extract_metadata(response.text, response.url or url)

    def download_paper(
        self,
        paper_id: str,
        output_dir: Path,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Download paper PDF if available and save metadata JSON."""
        if formats is None:
            formats = ["pdf"]

        metadata = self.get_paper_metadata(paper_id)
        safe_id = sanitize_paper_id(metadata["paper_id"])
        output_dir.mkdir(parents=True, exist_ok=True)
        downloaded_files: List[str] = []

        # Save metadata.json
        meta_path = output_dir / f"{safe_id}_metadata.json"
        meta_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        downloaded_files.append(str(meta_path))

        # Download PDF if available
        if "pdf" in formats and metadata.get("pdf_url"):
            try:
                pdf_resp = self.http.get(metadata["pdf_url"])
                if pdf_resp and (
                    pdf_resp.content.startswith(b"%PDF")
                    or "pdf" in pdf_resp.headers.get("content-type", "").lower()
                ):
                    pdf_path = output_dir / f"{safe_id}.pdf"
                    pdf_path.write_bytes(pdf_resp.content)
                    downloaded_files.append(str(pdf_path))
                else:
                    logger.info(
                        f"PDF no accesible directamente para {paper_id} ({metadata.get('pdf_url')})"
                    )
            except Exception as e:
                logger.warning(f"No se pudo descargar el PDF de {paper_id}: {e}")

        return {"success": True, "paper_id": safe_id, "files": downloaded_files}

    def get_repository_info(self) -> Dict[str, Any]:
        """Return basic repository metadata."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "description": "Repositório da Produção da Universidade de São Paulo (USP)",
            "supported_formats": ["pdf", "metadata"],
            "notes": "Web scraping on Repositório da Produção USP (BDPI)",
        }
