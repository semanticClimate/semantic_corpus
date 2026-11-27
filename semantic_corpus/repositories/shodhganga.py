"""Shodhganga repository implementation (shodhganga.inflibnet.ac.in HTML scraping)."""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import (
    handle_from_shodhganga_url,
    sanitize_paper_id,
)
from semantic_corpus.repositories._scraper import RateLimitedSession

logger = logging.getLogger(__name__)


class ShodhgangaRepository(RepositoryInterface):
    """Adapter for Shodhganga: a reservoir of Indian theses @ INFLIBNET.

    Handles DSpace platform with Anubis Proof-of-Work anti-bot challenge
    and referer-protected bitstream/PDF downloads.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "SHODHGANGA"
        self.base_url = "https://shodhganga.inflibnet.ac.in"
        self.search_url = "https://shodhganga.inflibnet.ac.in/simple-search"
        self.browse_url = "https://shodhganga.inflibnet.ac.in/browse?type=title"
        self.http = RateLimitedSession(
            delay_seconds=0.5,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) "
                "Gecko/20100101 Firefox/120.0"
            ),
        )
        self.http.session.headers.update(
            {
                "Referer": "https://shodhganga.inflibnet.ac.in/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

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
                        h = hashlib.sha256(
                            (rand_data + str(nonce)).encode("utf-8")
                        ).hexdigest()
                        if h.startswith(prefix):
                            break
                        nonce += 1
                    req_obj = getattr(resp, "request", None)
                    redir = (
                        getattr(req_obj, "path_url", "/browse?type=title")
                        if req_obj
                        else "/browse?type=title"
                    )
                    pass_url = (
                        f"{self.base_url}/.within.website/x/cmd/anubis/api/pass-challenge"
                        f"?id={chall['id']}&response={h}&nonce={nonce}&redir={redir}&elapsedTime=100"
                    )
                    resp = self.http.session.get(pass_url, **kwargs)
            except Exception as e:
                logger.warning(f"Error while solving Anubis challenge: {e}")
        return resp

    def _extract_article_links(self, html: str) -> List[str]:
        """Extracts unique item links from search or browse HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []
        for anchor in soup.select('a[href*="/handle/"]'):
            href = anchor.get("href", "").strip()
            if not href or any(
                p in href for p in ["/browse", "/community-list", "/simple-search"]
            ):
                continue
            match = re.search(r"/handle/(\d+(?:\.\d+)?)/(\d+)", href)
            if match:
                full_url = f"{self.base_url}/handle/{match.group(1)}/{match.group(2)}"
                if full_url not in links:
                    links.append(full_url)
        return links

    def _extract_metadata(self, html: str, article_url: str) -> Dict[str, Any]:
        """Extracts metadata fields from an item page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        paper_id = handle_from_shodhganga_url(article_url)

        def meta(name: str) -> str:
            el = (
                soup.select_one(f'meta[name="{name}"]')
                or soup.select_one(f'meta[name="DC.{name}"]')
                or soup.select_one(f'meta[name="DCTERMS.{name}"]')
                or soup.select_one(f'meta[property="{name}"]')
            )
            return el.get("content", "").strip() if el else ""

        # Title
        title = meta("citation_title") or meta("DC.title") or meta("title")
        if not title:
            for tr in soup.select("table.itemDisplayTable tr, table tr"):
                tds = tr.find_all(["th", "td"])
                if len(tds) >= 2 and "title" in tds[0].get_text(strip=True).lower():
                    title = tds[1].get_text(strip=True)
                    break
        if not title and soup.title:
            title = (
                soup.title.get_text(strip=True)
                .replace("Shodhganga@INFLIBNET:", "")
                .strip()
            )

        # Authors / Researchers
        authors = [
            el.get("content", "").strip()
            for el in (
                soup.select('meta[name="citation_author"]')
                + soup.select('meta[name="DC.creator"]')
            )
            if el.get("content") and el.get("content").strip()
        ]
        if not authors:
            for tr in soup.select("table.itemDisplayTable tr, table tr"):
                tds = tr.find_all(["th", "td"])
                if len(tds) >= 2 and any(
                    k in tds[0].get_text(strip=True).lower()
                    for k in ["researcher", "author"]
                ):
                    authors = [tds[1].get_text(strip=True)]
                    break
        authors = list(dict.fromkeys(authors))

        # Guide / Advisor / Contributor
        guides = [
            el.get("content", "").strip()
            for el in soup.select('meta[name="DC.contributor"]')
            if el.get("content") and el.get("content").strip()
        ]
        if not guides:
            for tr in soup.select("table.itemDisplayTable tr, table tr"):
                tds = tr.find_all(["th", "td"])
                if len(tds) >= 2 and "guide" in tds[0].get_text(strip=True).lower():
                    guides = [tds[1].get_text(strip=True)]
                    break

        # Abstract
        abstract = (
            meta("citation_abstract")
            or meta("DCTERMS.abstract")
            or meta("DC.description")
            or meta("description")
        )
        if abstract == "newline":
            abstract = ""
        if not abstract:
            for tr in soup.select("table.itemDisplayTable tr, table tr"):
                tds = tr.find_all(["th", "td"])
                if len(tds) >= 2 and "abstract" in tds[0].get_text(strip=True).lower():
                    txt = tds[1].get_text(strip=True)
                    if txt and txt.lower() != "newline":
                        abstract = txt
                    break

        # University / Publisher
        university = ""
        for tr in soup.select("table.itemDisplayTable tr, table tr"):
            tds = tr.find_all(["th", "td"])
            if len(tds) >= 2 and "university" in tds[0].get_text(strip=True).lower():
                university = tds[1].get_text(strip=True)
                break
        if not university:
            publishers = [
                el.get("content", "").strip()
                for el in soup.select('meta[name="DC.publisher"]')
                if el.get("content") and el.get("content").strip()
            ]
            for p in publishers:
                if any(w in p.lower() for w in ["univ", "inst", "colleg"]):
                    university = p
                    break
            if not university and publishers:
                university = publishers[0]
            if not university:
                university = (
                    meta("citation_dissertation_institution")
                    or meta("citation_publisher")
                    or "INFLIBNET Centre - Shodhganga"
                )

        # Date
        publication_date = (
            meta("citation_date")
            or meta("citation_publication_date")
            or meta("DC.date")
            or meta("DCTERMS.dateAccepted")
        )
        if not publication_date:
            for tr in soup.select("table.itemDisplayTable tr, table tr"):
                tds = tr.find_all(["th", "td"])
                if len(tds) >= 2 and any(
                    k in tds[0].get_text(strip=True).lower()
                    for k in ["completed date", "date"]
                ):
                    publication_date = tds[1].get_text(strip=True)
                    break

        # Bitstream / PDF URL
        pdf_url = meta("citation_pdf_url")
        pdf_urls: List[str] = []
        for anchor in soup.select('a[href*="/bitstream/"], a[href*=".pdf"]'):
            href = anchor.get("href", "").strip()
            if href:
                full_pdf = urljoin(self.base_url, href)
                if full_pdf not in pdf_urls:
                    pdf_urls.append(full_pdf)

        if not pdf_url and pdf_urls:
            # Prefer full thesis or first chapter
            full_thesis = [
                u
                for u in pdf_urls
                if any(t in u.lower() for t in ["full", "thesis", "complete"])
            ]
            pdf_url = full_thesis[0] if full_thesis else pdf_urls[0]

        if pdf_url and not pdf_url.startswith("http"):
            pdf_url = urljoin(self.base_url, pdf_url)

        # Keywords / Subjects
        keywords = [
            el.get("content", "").strip()
            for el in (
                soup.select('meta[name="citation_keywords"]')
                + soup.select('meta[name="DC.subject"]')
            )
            if el.get("content") and el.get("content").strip()
        ]

        return {
            "paper_id": paper_id,
            "url": article_url,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "guides": guides,
            "journal": university,
            "publisher": university,
            "doi": meta("citation_doi") or meta("DC.identifier"),
            "publication_date": publication_date,
            "pdf_url": pdf_url,
            "pdf_urls": pdf_urls,
            "keywords": keywords,
            "source_repository": "shodhganga",
        }

    def search_papers(
        self,
        query: str,
        limit: int = 10,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Search papers in Shodhganga and extract metadata."""
        del start_date, end_date
        clean_query = query.strip("()\"' ")

        # Support browsing mode if requested or if query is empty
        browse_type = kwargs.get("browse")
        if browse_type or not clean_query:
            browse_url = self.browse_url
            params: Dict[str, Any] = {"rpp": min(limit, 20)}
            if clean_query:
                params["starts_with"] = clean_query
            response = self._get_with_anubis(browse_url, params=params)
        else:
            params = {"query": clean_query, "rpp": min(limit, 20)}
            response = self._get_with_anubis(self.search_url, params=params)

        if not response:
            raise RepositoryError(
                f"Could not connect to Shodhganga repository at {self.search_url} (query: {query})"
            )

        links = self._extract_article_links(response.text)[:limit]
        results: List[Dict[str, Any]] = []
        for link in links:
            try:
                art_resp = self._get_with_anubis(link)
                if not art_resp:
                    continue
                results.append(self._extract_metadata(art_resp.text, link))
                if len(results) >= limit:
                    break
            except Exception as e:
                logger.warning(f"Error processing Shodhganga document {link}: {e}")
                continue

        return results

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Fetch metadata for a paper given its ID or URL."""
        if paper_id.startswith("http"):
            url = paper_id
        else:
            clean = paper_id.replace("shodhganga_", "")
            if clean.isdigit():
                clean_handle = f"10603/{clean}"
            else:
                clean_handle = clean.replace("_", "/")
            url = f"{self.base_url}/handle/{clean_handle}"

        response = self._get_with_anubis(url)
        if not response:
            raise RepositoryError(
                f"Could not find document in Shodhganga repository, id: {paper_id}"
            )
        return self._extract_metadata(response.text, response.url or url)

    def download_paper(
        self,
        paper_id: str,
        output_dir: Path,
        formats: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Downloads PDF and stores metadata as JSON."""
        if formats is None:
            formats = ["pdf"]

        metadata = self.get_paper_metadata(paper_id)
        safe_id = sanitize_paper_id(metadata["paper_id"])
        output_dir.mkdir(parents=True, exist_ok=True)
        downloaded_files: List[str] = []

        # 1. Store metadata.json
        meta_path = output_dir / f"{safe_id}_metadata.json"
        meta_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        downloaded_files.append(str(meta_path))

        # 2. Download PDF, if available
        if "pdf" in formats and metadata.get("pdf_url"):
            pdf_url = metadata["pdf_url"]
            # Set Referer to article handle page to prevent redirect to port 8443
            headers = {"Referer": metadata.get("url", f"{self.base_url}/")}
            pdf_resp = self._get_with_anubis(
                pdf_url, headers=headers, allow_redirects=True, timeout=30
            )
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
            "browse_url": self.browse_url,
            "description": "Shodhganga: a reservoir of Indian theses @ INFLIBNET",
            "supported_formats": ["pdf", "metadata"],
            "notes": "DSpace platform with Anubis anti-bot challenge and referer-protected bitstreams",
        }
