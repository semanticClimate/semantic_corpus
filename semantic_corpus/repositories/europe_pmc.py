"""Europe PMC repository implementation."""

import io
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from semantic_corpus.core.exceptions import RepositoryError
from semantic_corpus.core.repository_interface import RepositoryInterface
from semantic_corpus.repositories.document_content import (
    http_status_from_error_body,
    is_valid_document_file,
    looks_like_fulltext_xml,
    looks_like_pdf,
    safe_write_document,
)

# Re-export validators used by diagnostics / tests.
__all__ = [
    "EuropePMCRepository",
    "http_status_from_error_body",
    "interpret_epmc_error",
    "looks_like_fulltext_xml",
    "normalize_epmc_search_payload",
]

# PMC Article Datasets on AWS Open Data: updated daily, one folder per
# article version, e.g. PMC13380480.1/PMC13380480.1.pdf
PMC_OA_S3 = "https://pmc-oa-opendata.s3.amazonaws.com"
# Bulk open-access PDF mirror (what europepmc.org/ftp/pdf/ points to); lags
# behind the newest articles and has gaps
EUROPE_PMC_OA_PDF_FTP = "https://ftp.ebi.ac.uk/pub/databases/pmc/pdf/OA"
PDF_TIMEOUT_SECONDS = 60
SEARCH_TIMEOUT_SECONDS = 60

# Human-oriented hints for known Europe PMC errCode / HTTP statuses
_EPMC_ERROR_HINTS = {
    429: "Rate limited — wait and retry.",
    500: "Europe PMC internal error — retry later.",
    502: "Bad gateway — Europe PMC or a proxy is failing; retry later.",
    503: "Europe PMC search is temporarily unavailable — retry later.",
    504: "Gateway timeout — retry later.",
}


def interpret_epmc_error(
    *,
    status_code: Optional[int] = None,
    err_code: Any = None,
    err_msg: Optional[str] = None,
    body_preview: str = "",
) -> str:
    """Build a clear RepositoryError message for Europe PMC failures."""
    parts: List[str] = ["Europe PMC search failed"]
    code = err_code if err_code is not None else status_code
    if code is not None:
        parts.append(f"(code {code})")
    if err_msg:
        parts.append(f"— {err_msg}")
    elif status_code and not err_msg:
        parts.append(f"— HTTP {status_code}")
    hint_key = None
    try:
        hint_key = int(code) if code is not None else None
    except (TypeError, ValueError):
        hint_key = status_code
    hint = _EPMC_ERROR_HINTS.get(hint_key) if hint_key is not None else None
    if hint:
        parts.append(f"Hint: {hint}")
    if body_preview and not err_msg:
        parts.append(f"Body: {body_preview[:200]}")
    return " ".join(parts)


def normalize_epmc_search_payload(data: Any) -> Dict[str, Any]:
    """Validate and unwrap an Europe PMC search JSON body.

    Accepts both GET shape ``{hitCount, resultList, …}`` and POST/pygetpapers
    shape ``{responseWrapper: {hitCount, resultList, …}}``. Rejects null /
    error payloads (``errCode`` / ``errMsg``) with :class:`RepositoryError`.
    """
    if data is None:
        raise RepositoryError(
            interpret_epmc_error(err_msg="empty JSON body (null response)")
        )
    if not isinstance(data, dict):
        raise RepositoryError(
            interpret_epmc_error(
                err_msg=f"non-object JSON response ({type(data).__name__})"
            )
        )

    if "errCode" in data or "errMsg" in data:
        raise RepositoryError(
            interpret_epmc_error(
                err_code=data.get("errCode"),
                err_msg=data.get("errMsg") or "error payload without errMsg",
            )
        )

    # Unwrap POST / legacy responseWrapper if present
    if "responseWrapper" in data:
        wrapper = data.get("responseWrapper")
        if wrapper is None:
            raise RepositoryError(
                interpret_epmc_error(
                    err_msg="responseWrapper is null (pygetpapers-style KeyError cause)"
                )
            )
        if not isinstance(wrapper, dict):
            raise RepositoryError(
                interpret_epmc_error(
                    err_msg=f"responseWrapper is not an object ({type(wrapper).__name__})"
                )
            )
        if "errCode" in wrapper or "errMsg" in wrapper:
            raise RepositoryError(
                interpret_epmc_error(
                    err_code=wrapper.get("errCode"),
                    err_msg=wrapper.get("errMsg") or "error inside responseWrapper",
                )
            )
        data = wrapper

    if "hitCount" not in data and "resultList" not in data:
        raise RepositoryError(
            interpret_epmc_error(
                err_msg=(
                    "unexpected search payload "
                    f"(missing hitCount/resultList; keys={sorted(data.keys())})"
                )
            )
        )

    if data.get("hitCount") is None and data.get("resultList") is None:
        raise RepositoryError(
            interpret_epmc_error(err_msg="hitCount and resultList are both null")
        )

    return data


def _parse_epmc_response(response: requests.Response) -> Dict[str, Any]:
    """Parse HTTP response from Europe PMC search; raise on HTTP/API errors."""
    status = response.status_code
    text_preview = (response.text or "")[:300]

    # Try JSON even on error statuses — EPMC often returns {errCode, errMsg}
    data: Any = None
    try:
        data = response.json()
    except ValueError:
        data = None

    if status >= 400:
        err_code = None
        err_msg = None
        if isinstance(data, dict):
            err_code = data.get("errCode", status)
            err_msg = data.get("errMsg")
        raise RepositoryError(
            interpret_epmc_error(
                status_code=status,
                err_code=err_code,
                err_msg=err_msg,
                body_preview=text_preview if err_msg is None else "",
            )
        )

    return normalize_epmc_search_payload(data)


class EuropePMCRepository(RepositoryInterface):
    """Europe PMC repository implementation."""

    def __init__(self) -> None:
        """Initialize Europe PMC repository."""
        super().__init__()
        self.name = "Europe PMC"
        self.base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    def _paper_to_result(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a Europe PMC API paper record."""
        return {
            "pmcid": paper.get("pmcid", ""),
            "pmid": paper.get("pmid", ""),
            "title": paper.get("title", ""),
            "abstract": paper.get("abstractText", ""),
            "authors": paper.get("authorList", {}).get("author", []),
            "publication_date": paper.get("firstPublicationDate", ""),
            "journal": paper.get("journalTitle", ""),
            "doi": paper.get("doi", ""),
            "full_text_urls": paper.get("fullTextUrlList", {}).get("fullTextUrl", []),
            "has_pdf": paper.get("hasPDF", ""),
            "is_open_access": paper.get("isOpenAccess", ""),
        }

    def _search_one_paper(self, paper_id: str) -> Dict[str, Any]:
        """Fetch one Europe PMC record by external ID."""
        query = (
            f"PMCID:{paper_id}" if paper_id.startswith("PMC") else f"EXT_ID:{paper_id}"
        )
        params = {"query": query, "format": "json", "resultType": "core"}
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=SEARCH_TIMEOUT_SECONDS,
            )
        except requests.RequestException as e:
            raise RepositoryError(f"Europe PMC request failed: {e}") from e

        data = _parse_epmc_response(response)
        results = data.get("resultList", {}).get("result") or []
        if not results:
            raise RepositoryError(f"Paper {paper_id} not found")

        return results[0]

    @staticmethod
    def _s3_pdf_url(pmcid: str) -> Optional[str]:
        """Return the PMC Open Data (AWS S3) URL of the latest PDF version, if any."""
        try:
            response = requests.get(
                PMC_OA_S3,
                params={"list-type": "2", "prefix": f"{pmcid}."},
                timeout=PDF_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException:
            return None

        # Keys look like PMC123.2/PMC123.2.pdf; pick the highest version
        versions = [
            int(match)
            for match in re.findall(
                rf"<Key>{pmcid}\.(\d+)/{pmcid}\.\1\.pdf</Key>", response.text
            )
        ]
        if not versions:
            return None
        version = max(versions)
        return f"{PMC_OA_S3}/{pmcid}.{version}/{pmcid}.{version}.pdf"

    @staticmethod
    def _ftp_pdf_url(pmcid: str) -> str:
        """Return the EBI FTP URL of the zipped open-access PDF for a PMCID.

        Files are bucketed in groups of 10,000, e.g. PMC12911782 lives in
        PMCxxxx1292/PMC12911782.zip. This mirror is not behind Cloudflare,
        unlike the europepmc.org web endpoints.
        """
        number = int(pmcid[3:])
        bucket = -(-number // 10000)  # ceiling division
        return f"{EUROPE_PMC_OA_PDF_FTP}/PMCxxxx{bucket:03d}/{pmcid}.zip"

    @staticmethod
    def _full_text_pdf_urls(paper: Dict[str, Any]) -> List[str]:
        """Return free/open-access PDF links advertised in a Europe PMC record."""
        full_text_urls = paper.get("fullTextUrlList", {}).get("fullTextUrl", [])
        if isinstance(full_text_urls, dict):
            full_text_urls = [full_text_urls]

        return [
            entry["url"]
            for entry in full_text_urls
            if entry.get("documentStyle") == "pdf"
            and entry.get("availabilityCode") in ("OA", "F")
            and entry.get("url")
        ]

    @staticmethod
    def _fetch_pdf(url: str) -> Optional[bytes]:
        """Fetch a PDF (or a zip containing one); None if the response is not a PDF."""
        try:
            response = requests.get(url, timeout=PDF_TIMEOUT_SECONDS)
            response.raise_for_status()
        except requests.RequestException:
            return None

        content = response.content
        if url.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as archive:
                    names = [
                        n for n in archive.namelist() if n.lower().endswith(".pdf")
                    ]
                    content = archive.read(names[0]) if names else b""
            except zipfile.BadZipFile:
                return None

        # Cloudflare challenges / JSON error pages are not PDFs
        return content if looks_like_pdf(content) else None

    def _download_pdf(
        self, paper_id: str, paper: Optional[Dict[str, Any]], pmcid: str
    ) -> Optional[bytes]:
        """Try each known PDF source for a paper, most reliable first."""
        if pmcid:
            for url in (self._s3_pdf_url(pmcid), self._ftp_pdf_url(pmcid)):
                pdf = self._fetch_pdf(url) if url else None
                if pdf:
                    return pdf

        if paper is None:
            try:
                paper = self._search_one_paper(paper_id)
            except (RepositoryError, requests.RequestException):
                paper = {}

        candidates = self._full_text_pdf_urls(paper)
        if pmcid:
            # Web endpoint; often blocked for scripts by Cloudflare (HTTP 403)
            candidates.append(f"https://europepmc.org/articles/{pmcid}?pdf=render")

        for url in dict.fromkeys(candidates):
            pdf = self._fetch_pdf(url)
            if pdf:
                return pdf

        return None

    def search_papers(
        self,
        query: str,
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Search for papers in Europe PMC."""
        if not query or not str(query).strip():
            raise RepositoryError("Europe PMC search requires a non-empty query")

        params = {
            "query": query,
            "format": "json",
            "pageSize": min(limit, 1000),  # Europe PMC max is 1000
            "resultType": "core",
        }

        # Add date filters if provided
        if start_date and end_date:
            params["query"] = (
                f"({query}) AND (FIRST_PDATE:[{start_date} TO {end_date}])"
            )
        elif end_date:
            params["query"] = f"({query}) AND (FIRST_PDATE:[TO {end_date}])"

        try:
            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=SEARCH_TIMEOUT_SECONDS,
            )
        except requests.RequestException as e:
            raise RepositoryError(f"Europe PMC search failed: {e}") from e

        data = _parse_epmc_response(response)
        raw_results = data.get("resultList", {}).get("result") or []
        if isinstance(raw_results, dict):
            raw_results = [raw_results]

        results = [self._paper_to_result(paper) for paper in raw_results]
        return results[:limit]

    def get_paper_metadata(self, paper_id: str) -> Dict[str, Any]:
        """Get metadata for a specific paper from Europe PMC."""
        try:
            paper = self._search_one_paper(paper_id)
            return self._paper_to_result(paper)
        except RepositoryError:
            raise
        except requests.RequestException as e:
            raise RepositoryError(f"Failed to get metadata for {paper_id}: {e}") from e

    def download_paper(
        self,
        paper_id: str,
        output_dir: Path,
        formats: List[str] = None,
        *,
        paper: Optional[Dict[str, Any]] = None,
        streams: Optional[Any] = None,
        use_docling_xml: bool = True,
    ) -> Dict[str, Any]:
        """Download a paper from Europe PMC using independent JSON/XML/PDF streams.

        A 500 on one stream disables only that stream (via ``streams``). If XML
        is blocked/missing but PDF is available, Docling can create XML.
        """
        from semantic_corpus.pipeline.flat_corpus import (
            find_native_xml,
            find_paper_json,
            find_pdf,
            find_pdf_xml,
            paper_stem,
            path_pdf,
            path_pdf_xml,
            path_xml,
        )
        from semantic_corpus.repositories._ids import existing_document_paths
        from semantic_corpus.repositories.document_content import is_valid_document_file
        from semantic_corpus.repositories.epmc_streams import (
            STREAM_JSON,
            STREAM_PDF,
            STREAM_XML,
            EpmcStreamBoard,
            maybe_docling_pdf_to_xml,
            write_paper_metadata_json,
        )

        if formats is None:
            formats = ["xml"]
        formats = [f.strip().lower() for f in formats if f and str(f).strip()]
        board: EpmcStreamBoard = streams or EpmcStreamBoard()
        stem = paper_stem(paper_id)

        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            downloaded_files: List[str] = []
            stream_notes: List[str] = []

            want_xml = "xml" in formats
            want_pdf = "pdf" in formats or want_xml  # PDF also feeds Docling→XML
            track_formats = [
                f for f in ("xml", "pdf") if f in formats or (f == "pdf" and want_pdf)
            ]

            # Drop error stubs only; never delete valid documents.
            self._purge_invalid_stubs(output_dir, stem, track_formats)

            # Halt/restart: reuse anything already on disk (valid XML/PDF only).
            already = existing_document_paths(output_dir, stem, track_formats)
            for fmt, path in already.items():
                downloaded_files.append(str(path))
                stream_notes.append(f"skip-{fmt}")

            # JSON stream — flat ``{id}.json``; skip if present.
            if board.is_active(STREAM_JSON) and paper:
                meta_path = write_paper_metadata_json(output_dir, stem, paper)
                downloaded_files.append(str(meta_path))
                stream_notes.append("json")

            xml_path = path_xml(output_dir, stem)
            pdf_path = path_pdf(output_dir, stem)
            pdf_xml_path = path_pdf_xml(output_dir, stem)
            have_native_xml = find_native_xml(output_dir, stem) is not None
            have_pdf_xml = find_pdf_xml(output_dir, stem) is not None
            if have_pdf_xml:
                downloaded_files.append(str(pdf_xml_path))
                stream_notes.append("skip-pdf.xml")

            requested = [f for f in formats if f in ("xml", "pdf")]
            # Done enough: requested natives present, or XML need satisfied via .pdf.xml
            xml_satisfied = (not want_xml) or have_native_xml or have_pdf_xml
            pdf_satisfied = (not want_pdf) or ("pdf" in already)
            if requested and xml_satisfied and pdf_satisfied and find_paper_json(
                output_dir, stem
            ):
                return {
                    "success": True,
                    "paper_id": stem,
                    "files": downloaded_files,
                    "skipped": True,
                    "streams": stream_notes,
                    "xml": have_native_xml or have_pdf_xml,
                    "pdf": "pdf" in already,
                    "json": True,
                }

            pmcid = stem if stem.startswith("PMC") else ""
            download_id = ""
            local_paper = paper

            def _ensure_pmcid() -> str:
                nonlocal local_paper, pmcid, download_id
                if download_id:
                    return download_id
                if stem.startswith("PMC"):
                    pmcid = stem
                    download_id = stem.replace("PMC", "")
                    return download_id
                if paper_id.startswith("PPR"):
                    download_id = paper_id
                    return download_id
                if local_paper is None:
                    local_paper = self._search_one_paper(paper_id)
                pmcid = str(local_paper.get("pmcid") or "")
                if not pmcid:
                    raise RepositoryError(f"No PMCID found for {paper_id}")
                download_id = pmcid.replace("PMC", "")
                return download_id

            last_http: Optional[int] = None

            # --- XML stream → ``{id}.xml`` only (never Docling here) ---
            if want_xml and not have_native_xml and board.is_active(STREAM_XML):
                try:
                    _ensure_pmcid()
                    xml_url = f"{self.base_url}/PMC{download_id}/fullTextXML"
                    response = requests.get(xml_url)
                    response.raise_for_status()
                    content = response.content or b""
                    if not looks_like_fulltext_xml(content):
                        stub = http_status_from_error_body(content)
                        code = stub if stub is not None else (response.status_code or 500)
                        last_http = code
                        if code >= 500:
                            board.disable(
                                STREAM_XML,
                                reason="server error on fullTextXML",
                                status_code=code,
                            )
                            stream_notes.append(f"xml-off:{code}")
                    else:
                        wrote = safe_write_document(xml_path, content, fmt="xml")
                        if wrote or is_valid_document_file(xml_path, "xml"):
                            downloaded_files.append(str(xml_path))
                            stream_notes.append("xml")
                            have_native_xml = True
                except requests.HTTPError as e:
                    code = e.response.status_code if e.response is not None else 500
                    last_http = code
                    if code >= 500 or code in (403, 429):
                        board.disable(
                            STREAM_XML,
                            reason=f"HTTP {code} on fullTextXML",
                            status_code=code,
                        )
                        stream_notes.append(f"xml-off:{code}")
                except requests.RequestException:
                    stream_notes.append("xml-error")

            # --- PDF stream → ``{id}.pdf`` ---
            need_pdf = want_pdf or (
                want_xml and not have_native_xml and not have_pdf_xml
            )
            pmcid_error: Optional[str] = None
            if (
                need_pdf
                and "pdf" not in already
                and board.is_active(STREAM_PDF)
            ):
                try:
                    _ensure_pmcid()
                    pdf = self._download_pdf(stem, local_paper, pmcid)
                    if pdf and looks_like_pdf(pdf):
                        wrote = safe_write_document(pdf_path, pdf, fmt="pdf")
                        if wrote or is_valid_document_file(pdf_path, "pdf"):
                            downloaded_files.append(str(pdf_path))
                            stream_notes.append("pdf")
                    else:
                        stream_notes.append("pdf-miss")
                except RepositoryError as e:
                    pmcid_error = str(e)
                    stream_notes.append("no_pmcid")
                except requests.HTTPError as e:
                    code = e.response.status_code if e.response is not None else 500
                    last_http = code
                    if code >= 500 or code in (403, 429):
                        board.disable(
                            STREAM_PDF,
                            reason=f"HTTP {code} on PDF",
                            status_code=code,
                        )
                        stream_notes.append(f"pdf-off:{code}")
                except requests.RequestException:
                    stream_notes.append("pdf-error")

            # --- Docling PDF → ``{id}.pdf.xml`` (never overwrite ``{id}.xml``) ---
            have_native_xml = find_native_xml(output_dir, stem) is not None
            have_pdf = find_pdf(output_dir, stem) is not None
            have_pdf_xml = find_pdf_xml(output_dir, stem) is not None
            if (
                want_xml
                and not have_native_xml
                and not have_pdf_xml
                and have_pdf
                and use_docling_xml
            ):
                made = maybe_docling_pdf_to_xml(pdf_path, pdf_xml_path)
                if made is not None:
                    downloaded_files.append(str(made))
                    stream_notes.append("xml-from-pdf")
                    have_pdf_xml = True
                else:
                    stream_notes.append("docling-miss")

            have_xml = have_native_xml or have_pdf_xml
            have_json = find_paper_json(output_dir, stem) is not None
            if not (have_xml or have_pdf or have_json or downloaded_files):
                if last_http is not None:
                    raise RepositoryError(
                        f"No files downloaded for {stem} (HTTP {last_http})",
                        status_code=int(last_http),
                    )
                if pmcid_error:
                    raise RepositoryError(pmcid_error)
                raise RepositoryError(f"No files downloaded for {stem}")

            return {
                "success": True,
                "paper_id": stem,
                "files": downloaded_files,
                "streams": stream_notes,
                "xml": have_xml,
                "pdf": have_pdf,
                "json": have_json,
            }

        except RepositoryError:
            raise
        except requests.HTTPError as e:
            code = (
                e.response.status_code
                if e.response is not None
                else None
            )
            raise RepositoryError(
                f"Failed to download {paper_id}"
                + (f" (HTTP {code})" if code is not None else f": {e}"),
                status_code=int(code) if code is not None else None,
            ) from e
        except requests.RequestException as e:
            raise RepositoryError(f"Failed to download {paper_id}: {e}") from e

    @staticmethod
    def _purge_invalid_stubs(
        output_dir: Path, paper_id: str, formats: List[str]
    ) -> None:
        """Remove non-document error stubs saved under XML/PDF names."""
        from semantic_corpus.repositories._ids import paper_id_stems

        output_dir = Path(output_dir)
        stems = paper_id_stems(paper_id)
        for fmt in formats:
            kind = str(fmt).strip().lower()
            if kind not in ("xml", "pdf"):
                continue
            for stem in stems:
                candidates = [
                    Path(output_dir, f"{stem}.{kind}"),
                    Path(output_dir, "documents", f"{stem}.{kind}"),
                    Path(output_dir, "documents", kind, f"{stem}.{kind}"),
                ]
                if kind == "xml":
                    # Docling sidecar may also be an error stub
                    candidates.append(Path(output_dir, f"{stem}.pdf.xml"))
                for path in candidates:
                    if path.is_file() and not is_valid_document_file(path, kind):
                        try:
                            path.unlink()
                        except OSError:
                            pass

    def get_repository_info(self) -> Dict[str, Any]:
        """Get information about Europe PMC repository."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "description": "Europe PMC is an open science platform that enables access to a world of biomedical literature",
            "supported_formats": ["xml", "pdf"],
            "max_results_per_query": 1000,
            "api_documentation": "https://europepmc.org/Help",
        }
