"""OpenAlex repository implementation."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories._ids import openalex_short_id, sanitize_paper_id


class OpenAlexRepository(RepositoryInterface):
    """OpenAlex scholarly catalog adapter."""

    def __init__(self, mailto: str = "contact@semanticclimate.org") -> None:
        super().__init__()
        self.name = "OpenAlex"
        self.base_url = "https://api.openalex.org"
        self.mailto = mailto

    def _request_params(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = {"mailto": self.mailto}
        if extra:
            params.update(extra)
        return params

    def _paper_to_result(self, work: Dict[str, Any]) -> Dict[str, Any]:
        openalex_id = openalex_short_id(work.get("id", ""))
        doi = work.get("doi") or ""
        if doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")

        authors = []
        for author in work.get("authorships") or []:
            name = (author.get("author") or {}).get("display_name")
            if name:
                authors.append(name)

        journal = ""
        primary_location = work.get("primary_location") or {}
        source = primary_location.get("source") or {}
        if source.get("display_name"):
            journal = source["display_name"]

        best_oa = work.get("best_oa_location") or {}
        pdf_url = best_oa.get("pdf_url") or ""
        paper_id = openalex_id or sanitize_paper_id(doi)

        abstract = self._reconstruct_abstract(work.get("abstract_inverted_index"))

        return {
            "paper_id": paper_id,
            "openalex_id": openalex_id,
            "doi": doi,
            "title": work.get("display_name") or work.get("title") or "",
            "abstract": abstract,
            "authors": authors,
            "publication_date": work.get("publication_date") or "",
            "journal": journal,
            "pdf_url": pdf_url,
            "is_open_access": work.get("open_access", {}).get("is_oa", False),
            "cited_by_count": work.get("cited_by_count", 0),
            "source_repository": "openalex",
        }

    @staticmethod
    def _reconstruct_abstract(inverted_index: Optional[Dict[str, List[int]]]) -> str:
        if not inverted_index:
            return ""
        words: List[tuple[int, str]] = []
        for word, positions in inverted_index.items():
            for position in positions:
                words.append((position, word))
        words.sort(key=lambda item: item[0])
        return " ".join(word for _, word in words)

    def _fetch_work(self, paper_id: str) -> Dict[str, Any]:
        work_id = paper_id
        if paper_id.startswith("10."):
            work_id = f"https://doi.org/{paper_id}"
        elif not paper_id.startswith("https://") and paper_id.startswith("W"):
            work_id = f"https://openalex.org/{paper_id}"

        encoded = quote(work_id, safe="")
        response = requests.get(
            f"{self.base_url}/works/{encoded}",
            params=self._request_params(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def search_papers(
        self,
        query: str,
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Search OpenAlex works."""
        try:
            filters: List[str] = []
            if start_date:
                filters.append(f"from_publication_date:{start_date}")
            if end_date:
                filters.append(f"to_publication_date:{end_date}")

            params = self._request_params(
                {
                    "search": query,
                    "per-page": min(limit, 200),
                    "cursor": "*",
                }
            )
            if filters:
                params["filter"] = ",".join(filters)

            results: List[Dict[str, Any]] = []
            while len(results) < limit:
                response = requests.get(
                    f"{self.base_url}/works",
                    params=params,
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                for work in payload.get("results") or []:
                    results.append(self._paper_to_result(work))
                    if len(results) >= limit:
                        break

                next_cursor = (payload.get("meta") or {}).get("next_cursor")
                if not next_cursor or not payload.get("results"):
                    break
                params["cursor"] = next_cursor

            return results[:limit]
        except requests.RequestException as exc:
            raise RepositoryError(f"OpenAlex search failed: {exc}") from exc

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Get metadata for one OpenAlex work."""
        try:
            work = self._fetch_work(paper_id)
            return self._paper_to_result(work)
        except requests.RequestException as exc:
            raise RepositoryError(f"Failed to get metadata for {paper_id}: {exc}") from exc

    def download_paper(
        self,
        paper_id: str,
        output_dir: Path,
        formats: List[str] = None,
    ) -> Dict[str, Any]:
        """Download OpenAlex work metadata and optional OA PDF."""
        if formats is None:
            formats = ["pdf"]

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            metadata = self.get_paper_metadata(paper_id)
            safe_id = sanitize_paper_id(metadata["paper_id"])
            downloaded_files: List[str] = []

            metadata_path = output_dir / f"{safe_id}_metadata.json"
            metadata_path.write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            downloaded_files.append(str(metadata_path))

            if "pdf" in formats and metadata.get("pdf_url"):
                response = requests.get(metadata["pdf_url"], timeout=60)
                response.raise_for_status()
                if response.content.startswith(b"%PDF") or "pdf" in (
                    response.headers.get("content-type", "").lower()
                ):
                    pdf_path = output_dir / f"{safe_id}.pdf"
                    pdf_path.write_bytes(response.content)
                    downloaded_files.append(str(pdf_path))

            if not downloaded_files:
                raise RepositoryError(f"No files downloaded for {paper_id}")

            return {
                "success": True,
                "paper_id": safe_id,
                "files": downloaded_files,
            }
        except RepositoryError:
            raise
        except requests.RequestException as exc:
            raise RepositoryError(f"Failed to download {paper_id}: {exc}") from exc

    def get_repository_info(self) -> Dict[str, Any]:
        """Return OpenAlex repository metadata."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "description": (
                "OpenAlex is an open catalog of scholarly papers, authors, journals, "
                "and institutions"
            ),
            "supported_formats": ["pdf", "metadata"],
            "max_results_per_query": 200,
            "api_documentation": "https://docs.openalex.org/",
        }
