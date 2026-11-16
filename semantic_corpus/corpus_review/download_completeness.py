"""Hard check that requested full-text downloads are present on disk."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from semantic_corpus.corpus_review.constants import (
    DOWNLOAD_INCOMPLETE_PREFIX,
    DOWNLOAD_STATUS_COMPLETE,
    DOWNLOAD_STATUS_INCOMPLETE,
    DOWNLOAD_STATUS_UNKNOWN,
)


def paper_filename_stems(paper: Dict[str, Any]) -> List[str]:
    """Candidate stems for flat query-dir downloads (PMCID, PMID, paper_id)."""
    stems: List[str] = []
    for key in ("pmcid", "pmid", "paper_id"):
        value = paper.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in stems:
            stems.append(text)
    return stems


def _file_present(query_dir: Path, stem: str, ext: str) -> bool:
    path = Path(query_dir, f"{stem}.{ext}")
    return path.is_file() and path.stat().st_size > 0


def paper_has_format(query_dir: Path, paper: Dict[str, Any], ext: str) -> bool:
    """True if any known stem has a non-empty file for this format."""
    for stem in paper_filename_stems(paper):
        if _file_present(query_dir, stem, ext):
            return True
    return False


def check_download_completeness(
    *,
    query_dir: Optional[Path],
    papers: Sequence[Dict[str, Any]],
    formats: Sequence[str],
    downloaded_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Verify each retrieved paper has each requested format on disk.

    Returns a status dict with message suitable for CLI and PRISMA diagrams.
    """
    formats_list = [str(fmt).strip().lstrip(".").lower() for fmt in formats if fmt]
    if not formats_list:
        formats_list = ["xml"]

    if query_dir is None or not Path(query_dir).is_dir():
        return {
            "status": DOWNLOAD_STATUS_UNKNOWN,
            "complete": False,
            "n_papers": len(papers),
            "formats": formats_list,
            "n_expected_files": 0,
            "n_present_files": 0,
            "n_missing_files": 0,
            "n_papers_complete": 0,
            "n_papers_incomplete": 0,
            "missing": [],
            "message": (
                f"{DOWNLOAD_INCOMPLETE_PREFIX}: cannot verify downloads "
                "(query_dir missing or unavailable)."
            ),
        }

    query_dir = Path(query_dir)
    missing: List[Dict[str, Any]] = []
    n_present = 0
    n_expected = len(papers) * len(formats_list)
    n_papers_complete = 0

    for paper in papers:
        stems = paper_filename_stems(paper)
        missing_formats: List[str] = []
        for ext in formats_list:
            if paper_has_format(query_dir, paper, ext):
                n_present += 1
            else:
                missing_formats.append(ext)
        if missing_formats:
            missing.append(
                {
                    "pmcid": paper.get("pmcid") or "",
                    "pmid": str(paper.get("pmid") or ""),
                    "paper_id": paper.get("paper_id") or "",
                    "doi": paper.get("doi") or "",
                    "title": (paper.get("title") or "")[:120],
                    "stems": stems,
                    "missing_formats": missing_formats,
                }
            )
        else:
            n_papers_complete += 1

    n_missing = n_expected - n_present
    n_papers_incomplete = len(papers) - n_papers_complete
    complete = n_missing == 0 and len(papers) > 0

    if len(papers) == 0:
        message = (
            f"{DOWNLOAD_INCOMPLETE_PREFIX}: no retrieved papers to check."
        )
        status = DOWNLOAD_STATUS_INCOMPLETE
        complete = False
    elif complete:
        message = (
            f"DOWNLOAD COMPLETE: all {len(papers)} papers have requested "
            f"formats {formats_list} under {query_dir}."
        )
        status = DOWNLOAD_STATUS_COMPLETE
    else:
        sample = missing[:5]
        sample_text = "; ".join(
            (
                f"{item.get('pmcid') or item.get('pmid') or item.get('doi') or '?'} "
                f"missing {item.get('missing_formats')}"
            )
            for item in sample
        )
        extra = ""
        if downloaded_count is not None:
            extra = (
                f" query_run.downloaded_count={downloaded_count}/"
                f"{len(papers)}."
            )
        message = (
            f"{DOWNLOAD_INCOMPLETE_PREFIX}: expected {n_expected} files "
            f"({len(papers)} papers × formats {formats_list}); "
            f"found {n_present} on disk in {query_dir}; "
            f"missing {n_missing} "
            f"({n_papers_incomplete} papers incomplete). "
            f"Examples: {sample_text}.{extra}"
        )
        status = DOWNLOAD_STATUS_INCOMPLETE

    return {
        "status": status,
        "complete": complete,
        "n_papers": len(papers),
        "formats": formats_list,
        "n_expected_files": n_expected,
        "n_present_files": n_present,
        "n_missing_files": n_missing,
        "n_papers_complete": n_papers_complete,
        "n_papers_incomplete": n_papers_incomplete,
        "missing": missing,
        "query_dir": str(query_dir),
        "message": message,
    }
