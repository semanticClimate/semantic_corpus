import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import handle_from_uchile_url, sanitize_paper_id
from semantic_corpus.repositories._scraper import RateLimitedSession


class UchileRepository(RepositoryInterface):
    """Adapter applies web scraping to Repositorio Académico Universidad de Chile"""

    def __init__(self) -> None:
        super().__init__()
        self.name = "UCHILE"
        self.base_url = "https://repositorio.uchile.cl"
        self.search_url = "https://repositorio.uchile.cl/discover"
        self.http = RateLimitedSession(delay_seconds=1.0)

    def _get_with_anubis(self, url: str, **kwargs: Any) -> Optional[Any]:
        """Performs GET and automatically solves Anubis Proof-of-Work challenge if presented."""
        resp = self.http.get(url, **kwargs)
        if not resp:
            return None
        if "anubis_challenge" in getattr(resp, "text", ""):
            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                challenge_tag = soup.find("script", id="anubis_challenge")
                if challenge_tag and challenge_tag.string:
                    data = json.loads(challenge_tag.string)
                    chall = data["challenge"]
                    rand_data = chall["randomData"]
                    diff = data.get("rules", {}).get("difficulty", 4)
                    prefix = "0" * diff
                    nonce = 0
                    while True:
                        h = hashlib.sha256((rand_data + str(nonce)).encode("utf-8")).hexdigest()
                        if h.startswith(prefix):
                            break
                        nonce += 1
                    req_obj = getattr(resp, "request", None)
                    redir = getattr(req_obj, "path_url", "/discover") if req_obj else "/discover"
                    pass_url = (
                        f"{self.base_url}/.within.website/x/cmd/anubis/api/pass-challenge"
                        f"?id={chall['id']}&response={h}&nonce={nonce}&redir={redir}&elapsedTime=100"
                    )
                    resp = self.http.session.get(pass_url, **kwargs)
            except Exception:
                pass
        return resp


    def _extract_article_links(self, html: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []
        for anchor in soup.select('a[href*="/handle/"]'):
            href = anchor.get("href", "")
            if not href or any(p in href for p in ["/browse", "/community-list"]):
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
        paper_id = handle_from_uchile_url(article_url)

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
            "journal": meta("citation_journal_title") or meta("citation_publisher") or "Universidad de Chile",
            "doi": meta("citation_doi"),
            "publication_date": meta("citation_publication_date") or meta("citation_date"),
            "pdf_url": pdf_url,
            "source_repository": "uchile",
        }

    def search_papers(
        self,
        query: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Looks for documents in Repositorio Académico Uchile and extracts metadata"""
        del start_date, end_date
        clean_query = query.strip('()"\' ')
        params = {"query": clean_query, "rpp": min(limit, 20)}
        response = self._get_with_anubis(self.search_url, params=params)
        if not response:
            raise RepositoryError(f"Error occurred while looking for: {query}")

        links = self._extract_article_links(response.text)[:limit]
        results: List[Dict[str, Any]] = []
        for link in links:
            art_resp = self._get_with_anubis(link)
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
            # Recovers URL using ID (e.g.: uchile_2250_110429 -> /handle/2250/110429)
            clean = paper_id.replace("uchile_", "")
            if clean.isdigit():
                clean_handle = f"2250/{clean}"
            else:
                clean_handle = clean.replace("_", "/")
            url = f"{self.base_url}/handle/{clean_handle}"

        response = self._get_with_anubis(url)
        if not response:
            raise RepositoryError(
                f"Could not find the document in the UCHILE repository, id: {paper_id}"
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
            pdf_resp = self._get_with_anubis(metadata["pdf_url"])
            if pdf_resp and (
                pdf_resp.content.startswith(b"%PDF")
                or "pdf" in pdf_resp.headers.get("content-type", "").lower()
            ):
                pdf_path = output_dir / f"{safe_id}.pdf"
                pdf_path.write_bytes(pdf_resp.content)
                downloaded_files.append(str(pdf_path))

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
            "name": self.name,
            "base_url": self.base_url,
            "description": "Repositorio Académico de la Universidad de Chile",
            "supported_formats": ["pdf", "metadata"],
            "notes": "Scraping on DSpace Repositorio Académico Uchile platform",
        }