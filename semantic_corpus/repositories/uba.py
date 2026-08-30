import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import id_from_uba_url, sanitize_paper_id
from semantic_corpus.repositories._scraper import RateLimitedSession

logger = logging.getLogger(__name__)


class UbaRepository(RepositoryInterface):

    SOURCES = {
        "exactas": {
            "name": "Exactas (FCEN)",
            "base_url": "https://bibliotecadigital.exactas.uba.ar",
            "search_url": "https://bibliotecadigital.exactas.uba.ar/collection/todo/search/TextQuery",
            "link_base": "https://bibliotecadigital.exactas.uba.ar",
        },
        "fauba": {
            "name": "FAUBA",
            "base_url": "https://ri.agro.uba.ar/greenstone3/",
            "search_url": "https://ri.agro.uba.ar/greenstone3/library/collection/todo/search/TextQuery",
            "link_base": "https://ri.agro.uba.ar/greenstone3/",
        },
    }

    def __init__(self) -> None:
        super().__init__()
        self.name = "UBA"
        self.base_url = "https://www.uba.ar"
        self.http = RateLimitedSession(delay_seconds=0.5)

    def _extract_article_links(self, html: str, source_key: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []
        excluded_patterns = ["/browse", "toc", "c=revistas", "a=p", "a=g", "pref.action", "search"]
        source_info = self.SOURCES.get(source_key, self.SOURCES["exactas"])
        link_base = source_info["link_base"]

        for anchor in soup.select('a[href*="/document/"]'):
            href = anchor.get("href", "")
            if not href or any(pattern in href for pattern in excluded_patterns):
                continue
            clean_href = href.split(";")[0]
            full_url = urljoin(link_base, clean_href)
            if full_url not in links:
                links.append(full_url)
        return links

    def _is_valid_paper(self, metadata: Dict[str, Any], soup: BeautifulSoup) -> bool:
        doc_type_el = (
            soup.select_one('meta[name="DC.type"]')
            or soup.select_one('meta[name="citation_type"]')
            or soup.select_one('meta[name="type"]')
        )
        if doc_type_el:
            type_val = doc_type_el.get("content", "").lower()
            invalid_types = ["issue", "volume", "periodical", "serial"]
            if any(inv == type_val for inv in invalid_types):
                return False

        title = metadata.get("title", "").lower()
        if (title.startswith("revista ") or "número completo" in title) and not metadata.get("authors"):
            return False

        return bool(metadata.get("title"))

    def _extract_metadata(self, html: str, article_url: str, source_key: Optional[str] = None) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")
        paper_id = id_from_uba_url(article_url)

        if not source_key:
            source_key = "fauba" if "agro.uba.ar" in article_url else "exactas"

        source_info = self.SOURCES.get(source_key, self.SOURCES["exactas"])
        base_url = source_info["base_url"]

        def meta(name: str) -> str:
            el = (
                soup.select_one(f'meta[name="{name}"]')
                or soup.select_one(f'meta[name="DC.{name}"]')
                or soup.select_one(f'meta[name="DCTERMS.{name}"]')
            )
            return el.get("content", "").strip() if el else ""

        title = (
            meta("citation_title")
            or meta("title")
            or (soup.title.get_text(strip=True) if soup.title else "")
        )
        if title.startswith("::") or title.startswith("-"):
            dc_title = soup.select_one('meta[name="DC.title"]')
            if dc_title and dc_title.get("content"):
                title = dc_title.get("content").strip()

        raw_authors = [
            el.get("content", "").strip()
            for el in (
                soup.select('meta[name="citation_author"]')
                + soup.select('meta[name="DC.creator"]')
                + soup.select('meta[name="author"]')
            )
            if el.get("content") and el.get("content").strip()
        ]
        authors = list(dict.fromkeys(raw_authors))

        # Abstract
        abstract = (
            meta("citation_abstract")
            or meta("abstract")
            or meta("description")
        )

        pdf_url = meta("citation_pdf_url")
        if not pdf_url:
            dc_id = meta("identifier")
            if dc_id and ".pdf" in dc_id.lower():
                pdf_url = dc_id
        if not pdf_url:
            pdf_anchor = soup.select_one('a[href*=".pdf"]') or soup.select_one('a[href*="/download/"]')
            if pdf_anchor:
                pdf_url = urljoin(base_url, pdf_anchor.get("href", ""))
        elif not pdf_url.startswith("http"):
            pdf_url = urljoin(base_url, pdf_url)

        if not pdf_url and source_key == "exactas" and "/collection/" in article_url and "/document/" in article_url:
            parts = article_url.split("/collection/")[-1].split("/document/")
            if len(parts) == 2:
                coll, doc = parts[0], parts[1]
                pdf_url = f"https://bibliotecadigital.exactas.uba.ar/download/{coll}/{doc}.pdf"

        # publication date
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
            or f"Universidad de Buenos Aires ({source_info['name']})"
        )

        doi = meta("citation_doi") or meta("doi")

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
            "source_repository": "uba",
            "faculty": source_info["name"],
        }

    def _search_source(self, source_key: str, clean_query: str, limit: int) -> List[Dict[str, Any]]:
        source_info = self.SOURCES[source_key]
        params = {
            "qs": "1",
            "rt": "rd",
            "s1.level": "Doc",
            "s1.startPage": "1",
            "s1.query": clean_query,
        }

        try:
            response = self.http.get(source_info["search_url"], params=params)
            if not response:
                return []
            links = self._extract_article_links(response.text, source_key)
        except Exception as e:
            logger.warning(f"Error al consultar {source_info['name']}: {e}")
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
                metadata = self._extract_metadata(art_resp.text, link, source_key)

                if self._is_valid_paper(metadata, soup):
                    results.append(metadata)
            except Exception as e:
                logger.warning(f"Error al procesar documento {link}: {e}")
                continue

        return results

    def search_papers(
        self,
        query: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        del start_date, end_date
        clean_query = query.strip('()"\' ')

        faculty_filter = kwargs.get("faculty") or kwargs.get("source")
        if faculty_filter:
            faculty_key = str(faculty_filter).lower()
            if faculty_key in self.SOURCES:
                return self._search_source(faculty_key, clean_query, limit)

        # Exactas and FAUBA work together. They stand for the general UBA repo
        exactas_limit = (limit + 1) // 2
        fauba_limit = limit // 2

        exactas_results = self._search_source("exactas", clean_query, exactas_limit)
        fauba_results = self._search_source("fauba", clean_query, fauba_limit)

        # the two work together
        if len(exactas_results) < exactas_limit and len(fauba_results) == fauba_limit:
            extra = limit - len(exactas_results) - len(fauba_results)
            if extra > 0:
                more_fauba = self._search_source("fauba", clean_query, fauba_limit + extra)
                fauba_results = more_fauba
        elif len(fauba_results) < fauba_limit and len(exactas_results) == exactas_limit:
            extra = limit - len(exactas_results) - len(fauba_results)
            if extra > 0:
                more_exactas = self._search_source("exactas", clean_query, exactas_limit + extra)
                exactas_results = more_exactas


        combined: List[Dict[str, Any]] = []
        i, j = 0, 0
        while len(combined) < limit and (i < len(exactas_results) or j < len(fauba_results)):
            if i < len(exactas_results):
                combined.append(exactas_results[i])
                i += 1
            if len(combined) < limit and j < len(fauba_results):
                combined.append(fauba_results[j])
                j += 1

        return combined[:limit]

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """URL or ID as metadata source"""
        if paper_id.startswith("http"):
            url = paper_id
            source_key = "fauba" if "agro.uba.ar" in url else "exactas"
        elif paper_id.startswith("uba_exactas_"):
            parts = paper_id.replace("uba_exactas_", "").split("_", 1)
            coll = parts[0] if len(parts) > 1 else "tesis"
            doc = parts[1] if len(parts) > 1 else parts[0]
            url = f"https://bibliotecadigital.exactas.uba.ar/collection/{coll}/document/{doc}"
            source_key = "exactas"
        elif paper_id.startswith("uba_fauba_"):
            parts = paper_id.replace("uba_fauba_", "").split("_", 1)
            coll = parts[0] if len(parts) > 1 else "ti"
            doc = parts[1] if len(parts) > 1 else parts[0]
            url = f"https://ri.agro.uba.ar/greenstone3/library/collection/{coll}/document/{doc}"
            source_key = "fauba"
        else:
            # Fallback
            clean = paper_id.replace("uba_", "")
            parts = clean.split("_", 1)
            coll = parts[0] if len(parts) > 1 else "tesis"
            doc = parts[1] if len(parts) > 1 else parts[0]
            url = f"https://bibliotecadigital.exactas.uba.ar/collection/{coll}/document/{doc}"
            source_key = "exactas"

        response = self.http.get(url)
        if not response:
            raise RepositoryError(f"No se pudo encontrar el documento en el repositorio UBA, id: {paper_id}")
        return self._extract_metadata(response.text, response.url, source_key)

    def download_paper(
        self,
        paper_id: str,
        output_dir: Path,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Descarga el PDF (si está disponible abiertamente) y guarda los metadatos en JSON."""
        if formats is None:
            formats = ["pdf"]

        metadata = self.get_paper_metadata(paper_id)
        safe_id = sanitize_paper_id(metadata["paper_id"])
        output_dir.mkdir(parents=True, exist_ok=True)
        downloaded_files: List[str] = []

        # save metadata.json
        meta_path = output_dir / f"{safe_id}_metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        downloaded_files.append(str(meta_path))

        # PDF download - if available
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
                    logger.info(f"PDF no accesible públicamente para {paper_id} ({metadata.get('pdf_url')})")
            except Exception as e:
                logger.warning(f"No se pudo descargar el PDF de {paper_id}: {e}")

        return {"success": True, "paper_id": safe_id, "files": downloaded_files}

    def get_repository_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "description": "Repositorios Digitales de la Universidad de Buenos Aires (Exactas FCEN y Agronomía FAUBA)",
            "supported_formats": ["pdf", "metadata"],
            "notes": "Greenstone 3 platform for Exactas FCEN and FAUBA",
        }