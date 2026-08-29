import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import id_from_uba_url, sanitize_paper_id
from semantic_corpus.repositories._scraper import RateLimitedSession


class UbaRepository(RepositoryInterface):

    def __init__(self) -> None:
        super().__init__()
        self.name = "UBA_SISBI"
        self.base_url = "https://repositoriouba.sisbi.uba.ar"
        self.cgi_url = "https://repositoriouba.sisbi.uba.ar/gsdl/cgi-bin/library.cgi"
        self.http = RateLimitedSession(delay_seconds=1.0)

    def _extract_article_links(self, html: str) -> List[str]:
        """Extrae enlaces a documentos individuales (a=d) del HTML de resultados."""
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []
        excluded_patterns = ["/browse", "toc", "c=revistas", "a=p", "a=g"]

        for anchor in soup.select('a[href*="a=d"]'):
            href = anchor.get("href", "")
            if not href or any(pattern in href for pattern in excluded_patterns):
                continue
            full_url = urljoin(self.base_url, href)
            if full_url not in links:
                links.append(full_url)
        return links

    def _is_valid_paper(self, metadata: Dict[str, Any], soup: BeautifulSoup) -> bool:
        """Filtra para descartar revistas completas, números enteros o índices."""
        # 1. Comprobar tipo de ítem en etiquetas Dublin Core / Citation
        doc_type_el = (
                soup.select_one('meta[name="DC.type"]')
                or soup.select_one('meta[name="citation_type"]')
                or soup.select_one('meta[name="type"]')
        )
        if doc_type_el:
            type_val = doc_type_el.get("content", "").lower()
            invalid_types = ["journal", "revista", "issue", "volume", "periodical", "serial"]
            if any(inv in type_val for inv in invalid_types):
                return False

        # 2. Descartar si el título corresponde a una revista completa o volumen sin autor
        title = metadata.get("title", "").lower()
        if (title.startswith("revista ") or "número completo" in title or "volumen" in title) and not metadata.get(
                "authors"):
            return False

        return True

    def _extract_metadata(self, html: str, article_url: str) -> Dict[str, Any]:
        """Extrae metadatos del documento desde etiquetas <meta> o HTML."""
        soup = BeautifulSoup(html, "html.parser")
        paper_id = id_from_uba_url(article_url)

        def meta(name: str) -> str:
            el = soup.select_one(f'meta[name="{name}"]') or soup.select_one(f'meta[name="DC.{name}"]')
            return el.get("content", "").strip() if el else ""

        title = meta("citation_title") or meta("title") or (soup.title.get_text(strip=True) if soup.title else "")

        # Autores: combinar citation_author y DC.creator
        authors = [
            el.get("content", "").strip()
            for el in (soup.select('meta[name="citation_author"]') + soup.select('meta[name="DC.creator"]'))
            if el.get("content")
        ]

        abstract = meta("citation_abstract") or meta("description")

        # URL del PDF
        pdf_url = meta("citation_pdf_url")
        if not pdf_url:
            pdf_anchor = soup.select_one('a[href$=".pdf"]')
            if pdf_anchor:
                pdf_url = urljoin(self.base_url, pdf_anchor.get("href", ""))
        elif not pdf_url.startswith("http"):
            pdf_url = urljoin(self.base_url, pdf_url)

        return {
            "paper_id": paper_id,
            "url": article_url,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": meta("citation_journal_title") or meta("publisher"),
            "doi": meta("citation_doi"),
            "publication_date": meta("citation_publication_date") or meta("date"),
            "pdf_url": pdf_url,
            "source_repository": "uba",
        }

    def search_papers(
            self,
            query: str,
            limit: int = 10,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Busca documentos en Greenstone y extrae metadatos."""
        del start_date, end_date
        clean_query = query.strip('()"\' ')

        params = {
            "a": "q",
            "sa": "1",
            "q": clean_query,
            "rt": "rd",
        }
        # Si se pasa una colección específica por kwargs (ej. c="posgrauba")
        if "collection" in kwargs:
            params["c"] = kwargs["collection"]

        response = self.http.get(self.cgi_url, params=params)
        if not response:
            raise RepositoryError(f"Error al buscar en UBA SISBI para: {query}")

        links = self._extract_article_links(response.text)[:limit * 2]
        results: List[Dict[str, Any]] = []

        for link in links:
            art_resp = self.http.get(link)
            if not art_resp:
                continue

            soup = BeautifulSoup(art_resp.text, "html.parser")
            metadata = self._extract_metadata(art_resp.text, link)

            # Filtro: asegurar que sea un paper y no revista completa
            if not self._is_valid_paper(metadata, soup):
                continue

            results.append(metadata)
            if len(results) >= limit:
                break

        return results

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Obtiene metadatos a partir de URL o identificador 'uba_coleccion_id'."""
        if paper_id.startswith("http"):
            url = paper_id
        else:
            # Reconstruye la URL de Greenstone desde el ID (ej: uba_posgrauba_HWEB01)
            clean = paper_id.replace("uba_", "")
            parts = clean.split("_", 1)
            coll = parts[0] if len(parts) > 1 else ""
            doc = parts[1] if len(parts) > 1 else parts[0]
            url = f"{self.cgi_url}?a=d&c={coll}&d={doc}"

        response = self.http.get(url)
        if not response:
            raise RepositoryError(f"No se pudo encontrar el documento en el repositorio UBA SISBI, id: {paper_id}")
        return self._extract_metadata(response.text, response.url)

    def download_paper(
            self,
            paper_id: str,
            output_dir: Path,
            formats: List[str] = None,
    ) -> Dict[str, Any]:
        """Descarga el PDF y guarda los metadatos en JSON."""
        if formats is None:
            formats = ["pdf"]

        metadata = self.get_paper_metadata(paper_id)
        safe_id = sanitize_paper_id(metadata["paper_id"])
        output_dir.mkdir(parents=True, exist_ok=True)
        downloaded_files: List[str] = []

        # 1. Guardar metadata.json
        meta_path = output_dir / f"{safe_id}_metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        downloaded_files.append(str(meta_path))

        # 2. Descargar PDF si está disponible
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
            "description": "Repositorio Digital Institucional UBA (SISBI)",
            "supported_formats": ["pdf", "metadata"],
            "notes": "Scraping on Greenstone Digital Library (GSDL) platform",
        }