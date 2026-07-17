"""Build PRISMA-like screening flow counts from query run and review table."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import json
import yaml

from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.constants import (
    DOWNLOAD_STATUS_UNKNOWN,
    PRISMA_REASON_BEYOND_LIMIT,
    PRISMA_REASON_DOWNLOAD_FAILED,
    PRISMA_REASON_FULLTEXT_UNAVAILABLE,
    PRISMA_REASON_MANUAL_EXCLUDE,
    PRISMA_REASON_PENDING_REVIEW,
    REVIEW_STATUS_EXCLUDE,
    REVIEW_STATUS_INCLUDE,
    REVIEW_STATUS_REVIEW,
)
from semantic_corpus.corpus_review.download_completeness import (
    check_download_completeness,
)
from semantic_corpus.corpus_review.query_run import load_query_run_record


def load_review_table_rows(path: Path) -> List[Dict[str, Any]]:
    """Load review_table.json as a list of row dicts."""
    path = Path(path)
    if not path.is_file():
        raise CorpusError(f"Review table not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("rows", "papers", "review_table"):
            rows = data.get(key)
            if isinstance(rows, list):
                return rows
    raise CorpusError(f"Review table must be a list of rows: {path}")


def load_prisma_overrides(path: Optional[Path]) -> Dict[str, Any]:
    """Load optional prisma_overrides.yaml (n_identified and notes)."""
    if path is None:
        return {}
    path = Path(path)
    if not path.is_file():
        raise CorpusError(f"PRISMA overrides file not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise CorpusError(f"PRISMA overrides must be a mapping: {path}")
    return data


def resolve_review_table_path(
    *,
    corpus_dir: Optional[Path] = None,
    query_dir: Optional[Path] = None,
    review_table: Optional[Path] = None,
) -> Path:
    """Prefer explicit path, then corpus analysis review, then query review."""
    if review_table is not None:
        return Path(review_table)
    candidates: List[Path] = []
    if corpus_dir is not None:
        corpus_dir = Path(corpus_dir)
        candidates.append(
            Path(corpus_dir, "data", "analysis", "review", "review_table.json")
        )
        candidates.append(Path(corpus_dir, "analysis", "review", "review_table.json"))
    if query_dir is not None:
        candidates.append(Path(query_dir, "review", "review_table.json"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    tried = ", ".join(str(path) for path in candidates) or "(none)"
    raise CorpusError(f"Could not find review_table.json. Tried: {tried}")


def default_prisma_output_dir(corpus_dir: Path) -> Path:
    """Corpora layout: data/analysis/prisma/."""
    return Path(corpus_dir, "data", "analysis", "prisma")


def _truthy_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y"}


def _count_status(rows: List[Dict[str, Any]], status: str) -> int:
    return sum(1 for row in rows if row.get("review_status") == status)


def _count_fulltext_flags(rows: List[Dict[str, Any]]) -> int:
    return sum(
        1
        for row in rows
        if _truthy_flag(row.get("has_xml")) or _truthy_flag(row.get("has_pdf"))
    )


def _repo_relative(path: Optional[Path], repo_root: Optional[Path]) -> str:
    if path is None:
        return ""
    path = Path(path)
    if not path.exists() and not path.is_file() and not path.is_dir():
        # Still show intended path
        pass
    if repo_root is not None:
        try:
            return str(path.resolve().relative_to(Path(repo_root).resolve()))
        except ValueError:
            return str(path)
    return str(path)


def _count_files(directory: Path, pattern: str) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for _ in directory.glob(pattern) if _.is_file())


def count_fulltext_on_disk(
    *,
    query_dir: Optional[Path] = None,
    corpus_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Count XML/PDF/HTML files in query dir and corpus document folders."""
    xml_n = 0
    pdf_n = 0
    html_n = 0
    locations: List[str] = []

    if query_dir is not None:
        query_dir = Path(query_dir)
        if query_dir.is_dir():
            q_xml = _count_files(query_dir, "*.xml")
            q_pdf = _count_files(query_dir, "*.pdf")
            q_html = _count_files(query_dir, "*.html")
            xml_n = max(xml_n, q_xml)
            pdf_n = max(pdf_n, q_pdf)
            html_n = max(html_n, q_html)
            locations.append(str(query_dir))

    if corpus_dir is not None:
        corpus_dir = Path(corpus_dir)
        doc_roots = [
            Path(corpus_dir, "data", "documents"),
            Path(corpus_dir, "data", "data", "documents"),
        ]
        for root in doc_roots:
            if not root.is_dir():
                continue
            xml_n = max(xml_n, _count_files(Path(root, "xml"), "*.xml"))
            pdf_n = max(pdf_n, _count_files(Path(root, "pdf"), "*.pdf"))
            html_n = max(html_n, _count_files(Path(root, "html"), "*.html"))
            # Also allow flat layouts
            xml_n = max(xml_n, _count_files(root, "*.xml"))
            pdf_n = max(pdf_n, _count_files(root, "*.pdf"))
            html_n = max(html_n, _count_files(root, "*.html"))
            locations.append(str(root))

    any_fulltext = max(xml_n, pdf_n, html_n)
    # Papers with at least one format: use max of formats as lower bound;
    # if query_dir has mixed IDs, max(xml,pdf) approximates "has fulltext".
    n_with_fulltext = max(xml_n, pdf_n, html_n)
    return {
        "n_xml": xml_n,
        "n_pdf": pdf_n,
        "n_html": html_n,
        "n_with_fulltext": n_with_fulltext,
        "locations": locations,
        "any_fulltext_files": any_fulltext,
    }


def _find_config_path(query_name: str, repo_root: Optional[Path]) -> Optional[Path]:
    if not query_name:
        return None
    roots = [repo_root] if repo_root else [Path.cwd()]
    for root in roots:
        candidate = Path(root, "config", f"{query_name}.yaml")
        if candidate.is_file():
            return candidate
    return None


def _artefact(
    role: str,
    path: Optional[Path],
    *,
    repo_root: Optional[Path],
    note: str = "",
    exists: Optional[bool] = None,
) -> Dict[str, Any]:
    path_obj = Path(path) if path is not None else None
    present = exists if exists is not None else (
        path_obj.is_file() or path_obj.is_dir() if path_obj else False
    )
    return {
        "role": role,
        "path": _repo_relative(path_obj, repo_root) if path_obj else "",
        "exists": present,
        "note": note,
    }


def build_prisma_flow(
    *,
    query_run_path: Optional[Path] = None,
    review_table_path: Path,
    search_results_path: Optional[Path] = None,
    overrides_path: Optional[Path] = None,
    corpus_dir: Optional[Path] = None,
    query_dir: Optional[Path] = None,
    config_path: Optional[Path] = None,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Assemble prisma_flow dict from query provenance and review decisions.

    Decisions baked in:
    - n_identified may come from overrides (preferred when set)
    - final included shows include and still-review separately
    - artefacts list local file paths used for each count
    """
    review_table_path = Path(review_table_path)
    rows = load_review_table_rows(review_table_path)
    overrides = load_prisma_overrides(overrides_path)

    if query_dir is None and search_results_path:
        query_dir = Path(search_results_path).parent
    if query_dir is None and query_run_path:
        query_dir = Path(query_run_path).parent

    record: Dict[str, Any] = {}
    if query_run_path and Path(query_run_path).is_file():
        record = load_query_run_record(query_run_path)

    query_name = (
        record.get("query_name")
        or (rows[0].get("query_name") if rows else "")
        or ""
    )
    query_string = (
        record.get("query_string")
        or (rows[0].get("query_string") if rows else "")
        or ""
    )

    if config_path is None:
        config_path = _find_config_path(str(query_name), repo_root)

    n_retrieved = None
    retrieved_source = "unknown"
    papers_for_download_check: List[Dict[str, Any]] = []
    if search_results_path and Path(search_results_path).is_file():
        with open(search_results_path, "r", encoding="utf-8") as handle:
            search_data = json.load(handle)
        if isinstance(search_data, list):
            n_retrieved = len(search_data)
            retrieved_source = "search_results.json length"
            papers_for_download_check = search_data
    if n_retrieved is None and record.get("result_count") is not None:
        n_retrieved = int(record["result_count"])
        retrieved_source = "query_run.result_count"
    if n_retrieved is None:
        n_retrieved = len(rows)
        retrieved_source = "review_table.json length"
    if not papers_for_download_check:
        papers_for_download_check = rows

    limit = record.get("limit")
    if limit is not None:
        limit = int(limit)

    # Identification: only treat as database-wide hitCount when override or total_hits.
    n_identified: Optional[int] = None
    identified_source = "unknown"
    identified_is_hitcount = False
    if overrides.get("n_identified") is not None:
        n_identified = int(overrides["n_identified"])
        identified_source = "overrides.n_identified"
        identified_is_hitcount = True
    elif record.get("total_hits") is not None:
        n_identified = int(record["total_hits"])
        identified_source = "query_run.total_hits"
        identified_is_hitcount = True
    else:
        n_identified = n_retrieved
        identified_source = (
            "same as retrieved (total hitCount not recorded; "
            "set prisma_overrides.yaml n_identified or query_run.total_hits)"
        )
        identified_is_hitcount = False

    n_beyond_limit = 0
    if identified_is_hitcount and n_identified is not None and limit is not None:
        n_beyond_limit = max(0, n_identified - limit)

    n_screened = len(rows)
    n_include = _count_status(rows, REVIEW_STATUS_INCLUDE)
    n_exclude = _count_status(rows, REVIEW_STATUS_EXCLUDE)
    n_still_review = _count_status(rows, REVIEW_STATUS_REVIEW)

    disk = count_fulltext_on_disk(query_dir=query_dir, corpus_dir=corpus_dir)
    flag_fulltext = _count_fulltext_flags(rows)
    # Prefer filesystem counts when any files are present.
    if disk["n_with_fulltext"] > 0:
        n_with_fulltext = int(disk["n_with_fulltext"])
        fulltext_source = (
            f"filesystem (xml={disk['n_xml']}, pdf={disk['n_pdf']}, "
            f"html={disk['n_html']})"
        )
    else:
        n_with_fulltext = flag_fulltext
        fulltext_source = "review_table has_xml/has_pdf flags"

    downloaded_count = record.get("downloaded_count")
    if downloaded_count is not None:
        downloaded_count = int(downloaded_count)
        n_download_failed = max(0, n_retrieved - downloaded_count)
        download_source = "query_run.downloaded_count"
    else:
        n_download_failed = max(0, n_retrieved - n_with_fulltext)
        download_source = "derived from fulltext gap"

    formats = record.get("formats") or ["xml"]
    download_check = check_download_completeness(
        query_dir=query_dir,
        papers=papers_for_download_check,
        formats=formats,
        downloaded_count=downloaded_count,
    )
    # Prefer hard per-file check for download_failed when available.
    if download_check.get("status") != DOWNLOAD_STATUS_UNKNOWN:
        n_download_failed = int(download_check.get("n_missing_files") or 0)
        download_source = "download_completeness hard check"

    exclusions: List[Dict[str, Any]] = []
    if n_beyond_limit:
        exclusions.append(
            {"reason": PRISMA_REASON_BEYOND_LIMIT, "n": n_beyond_limit}
        )
    n_fulltext_unavailable = max(0, n_retrieved - n_with_fulltext)
    if downloaded_count is not None:
        if n_download_failed:
            exclusions.append(
                {"reason": PRISMA_REASON_DOWNLOAD_FAILED, "n": n_download_failed}
            )
    elif n_fulltext_unavailable:
        exclusions.append(
            {
                "reason": PRISMA_REASON_FULLTEXT_UNAVAILABLE,
                "n": n_fulltext_unavailable,
            }
        )
    if n_exclude:
        exclusions.append(
            {"reason": PRISMA_REASON_MANUAL_EXCLUDE, "n": n_exclude}
        )
    if n_still_review:
        exclusions.append(
            {"reason": PRISMA_REASON_PENDING_REVIEW, "n": n_still_review}
        )

    artefacts = [
        _artefact(
            "raw_query",
            None,
            repo_root=repo_root,
            note=str(query_string),
            exists=bool(query_string),
        ),
        _artefact("config", config_path, repo_root=repo_root, note="pilot YAML"),
        _artefact(
            "query_run",
            query_run_path,
            repo_root=repo_root,
            note="repository, limit, result_count, downloaded_count",
        ),
        _artefact(
            "search_results",
            search_results_path,
            repo_root=repo_root,
            note="retrieved metadata records",
        ),
        _artefact(
            "query_dir_fulltext",
            query_dir,
            repo_root=repo_root,
            note=(
                f"local downloads xml={disk['n_xml']} "
                f"pdf={disk['n_pdf']} html={disk['n_html']}"
            ),
            exists=bool(query_dir and Path(query_dir).is_dir()),
        ),
        _artefact(
            "review_table",
            review_table_path,
            repo_root=repo_root,
            note="manual include/exclude/review statuses",
        ),
        _artefact(
            "overrides",
            overrides_path,
            repo_root=repo_root,
            note="optional n_identified hitCount",
        ),
        _artefact(
            "corpus_dir",
            corpus_dir,
            repo_root=repo_root,
            note="BAGIT corpus (diagram output target)",
            exists=bool(corpus_dir and Path(corpus_dir).is_dir()),
        ),
    ]

    count_provenance = {
        "n_identified": identified_source,
        "n_retrieved": retrieved_source,
        "n_with_fulltext": fulltext_source,
        "n_download_attempted": download_source,
        "n_screened": "review_table.json length",
        "n_include": "review_status=include",
        "n_exclude": "review_status=exclude",
        "n_still_review": "review_status=review",
        "n_final_table": "n_include + n_still_review",
    }

    flow = {
        "meta": {
            "query_name": query_name,
            "query_string": query_string,
            "repository": record.get("repository") or "",
            "start_date": record.get("start_date") or "",
            "end_date": record.get("end_date") or "",
            "limit": limit,
            "formats": record.get("formats") or [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "identified_source": identified_source,
            "identified_is_hitcount": identified_is_hitcount,
            "override_notes": overrides.get("notes") or "",
            "count_provenance": count_provenance,
            "disk_fulltext": {
                "n_xml": disk["n_xml"],
                "n_pdf": disk["n_pdf"],
                "n_html": disk["n_html"],
            },
        },
        "artefacts": artefacts,
        "download_check": download_check,
        "counts": {
            "n_identified": n_identified,
            "n_beyond_limit": n_beyond_limit,
            "n_retrieved": n_retrieved,
            "n_download_attempted": downloaded_count
            if downloaded_count is not None
            else n_retrieved,
            "n_with_fulltext": n_with_fulltext,
            "n_xml_on_disk": disk["n_xml"],
            "n_pdf_on_disk": disk["n_pdf"],
            "n_html_on_disk": disk["n_html"],
            "n_download_failed": n_download_failed,
            "n_screened": n_screened,
            "n_include": n_include,
            "n_exclude": n_exclude,
            "n_still_review": n_still_review,
            "n_included_final": n_include,
            "n_final_table": n_include + n_still_review,
        },
        "exclusions": exclusions,
    }
    validate_prisma_flow(flow)
    return flow


def validate_prisma_flow(flow: Dict[str, Any]) -> None:
    """Raise CorpusError if count invariants fail."""
    counts = flow.get("counts") or {}
    n_screened = int(counts.get("n_screened") or 0)
    n_include = int(counts.get("n_include") or 0)
    n_exclude = int(counts.get("n_exclude") or 0)
    n_still_review = int(counts.get("n_still_review") or 0)
    status_sum = n_include + n_exclude + n_still_review
    if status_sum != n_screened:
        raise CorpusError(
            f"Status counts ({status_sum}) must equal n_screened ({n_screened})"
        )
    n_final = int(counts.get("n_final_table") or 0)
    if n_final != n_include + n_still_review:
        raise CorpusError(
            "n_final_table must equal n_include + n_still_review "
            f"({n_include}+{n_still_review}!={n_final})"
        )


def write_prisma_flow_json(flow: Dict[str, Any], output_dir: Path) -> Path:
    """Write prisma_flow.json under output_dir."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir, "prisma_flow.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(flow, handle, indent=2, ensure_ascii=False)
    return out_path
