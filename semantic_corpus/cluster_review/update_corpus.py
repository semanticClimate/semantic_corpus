"""Update an existing BAGIT corpus with additional document files (e.g. PDFs).

Callable after Step 1 (or any later stage) without re-running the query harvest.
Europe PMC PDFs use the existing repository downloader (S3 / FTP / OA URLs)
and reject non-``%PDF`` bodies so HTML error pages are not saved as PDFs.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from semantic_corpus.cluster_review.step1 import (
    find_metadata_dir,
    find_review_table,
    load_bagit_corpus,
    resolve_bagit_root,
)
from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError, RepositoryError
from semantic_corpus.core.repository_factory import RepositoryFactory

DEFAULT_FORMATS = ("pdf",)
DEFAULT_REPOSITORY = "europe_pmc"
# Tiny / error HTML masquerading as PDF is typically well under this.
MIN_PDF_BYTES = 10_000

ProgressCallback = Callable[[int, int, str, str], None]


def pmcid_from_paper_id(paper_id: str) -> Optional[str]:
    """Extract ``PMC123`` from corpus ids like ``europe_pmc_PMC123`` or ``PMC123``."""
    text = str(paper_id or "").strip()
    if not text:
        return None
    match = re.search(r"PMC(\d+)", text, flags=re.IGNORECASE)
    if not match:
        return None
    return f"PMC{match.group(1)}"


def documents_dir_for_format(bag_root: Path, fmt: str) -> Path:
    """BAGIT ``data/documents/{fmt}/`` when present; else flat workdir root."""
    bag_root = Path(bag_root)
    fmt = fmt.strip().lower()
    candidates = [
        Path(bag_root, "data", "documents", fmt),
        Path(bag_root, "data", "data", "documents", fmt),
    ]
    for path in candidates:
        if path.is_dir():
            return path
    # Flat corpus: files live at workdir root (no per-format directories)
    if not Path(bag_root, "bagit.txt").is_file():
        return bag_root
    preferred = candidates[0]
    preferred.mkdir(parents=True, exist_ok=True)
    return preferred


def pdf_path_for_paper(bag_root: Path, paper_id: str) -> Path:
    from semantic_corpus.pipeline.flat_corpus import path_pdf

    bag_root = Path(bag_root)
    if not Path(bag_root, "bagit.txt").is_file():
        return path_pdf(bag_root, paper_id)
    return Path(documents_dir_for_format(bag_root, "pdf"), f"{paper_id}.pdf")


def is_valid_pdf(path: Path, *, min_bytes: int = MIN_PDF_BYTES) -> bool:
    """True if ``path`` is a non-tiny file starting with ``%PDF``."""
    path = Path(path)
    if not path.is_file():
        return False
    try:
        size = path.stat().st_size
    except OSError:
        return False
    if size < min_bytes:
        return False
    try:
        with open(path, "rb") as handle:
            head = handle.read(5)
    except OSError:
        return False
    return head.startswith(b"%PDF")


def _refresh_review_has_pdf(
    corpus_dir: Path,
    bag_root: Path,
    paper_ids: Sequence[str],
) -> Optional[Path]:
    """Update ``has_pdf`` on an existing review table when present."""
    review_path = find_review_table(corpus_dir, bag_root)
    if review_path is None or not review_path.is_file():
        return None
    with open(review_path, "r", encoding="utf-8") as handle:
        rows = json.load(handle)
    if not isinstance(rows, list):
        return None
    wanted = set(paper_ids)
    changed = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        paper_id = str(row.get("paper_id") or "")
        if paper_id not in wanted:
            continue
        has_pdf = is_valid_pdf(pdf_path_for_paper(bag_root, paper_id))
        if bool(row.get("has_pdf")) != has_pdf:
            row["has_pdf"] = has_pdf
            changed = True
    if changed:
        with open(review_path, "w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2, ensure_ascii=False)
    return review_path


def _download_europe_pmc_pdf(pmcid: str, dest: Path) -> None:
    """Fetch one PDF via Europe PMC and write to ``dest`` if valid."""
    repo = RepositoryFactory.get_repository("europe_pmc")
    with tempfile.TemporaryDirectory(prefix="sc_pdf_") as tmp:
        tmp_dir = Path(tmp)
        result = repo.download_paper(pmcid, tmp_dir, formats=["pdf"])
        files = result.get("files") or []
        # Prefer a path that looks like a PDF
        candidates = [Path(f) for f in files if str(f).lower().endswith(".pdf")]
        if not candidates:
            # Flat / documents layout from download_paper
            for pattern in (f"{pmcid}.pdf", f"documents/{pmcid}.pdf"):
                path = Path(tmp_dir, pattern)
                if path.is_file():
                    candidates.append(path)
        if not candidates:
            raise RepositoryError(f"No PDF returned for {pmcid}")
        src = candidates[0]
        if not is_valid_pdf(src):
            raise RepositoryError(
                f"Downloaded file for {pmcid} is not a valid PDF "
                f"(size={src.stat().st_size if src.is_file() else 0})"
            )
        from semantic_corpus.repositories.document_content import safe_write_document

        payload = src.read_bytes()
        if not safe_write_document(dest, payload, fmt="pdf"):
            raise RepositoryError(
                f"Refusing to write non-PDF (or overwrite) for {pmcid}"
            )


def update_bagit_formats(
    corpus_dir: Path,
    *,
    formats: Sequence[str] = DEFAULT_FORMATS,
    repository: str = DEFAULT_REPOSITORY,
    force: bool = False,
    paper_ids: Optional[Sequence[str]] = None,
    progress_callback: Optional[ProgressCallback] = None,
    min_pdf_bytes: int = MIN_PDF_BYTES,
) -> Dict[str, Any]:
    """Download missing document formats into an existing BAGIT corpus.

    Args:
        corpus_dir: BAGIT root (or parent containing bagit.txt).
        formats: Currently only ``pdf`` is supported.
        repository: Repository key (only ``europe_pmc`` for PDFs in this slice).
        force: Re-download even when a valid PDF is already present.
        paper_ids: Optional subset of corpus paper ids; default = all.
        progress_callback: Optional ``(i, total, paper_id, status)``.
        min_pdf_bytes: Reject smaller files (error HTML / stubs).

    Returns:
        Summary with downloaded / skipped / failed counts and per-paper details.
    """
    corpus_dir = Path(corpus_dir)
    bag_root = resolve_bagit_root(corpus_dir)
    fmt_list = [f.strip().lower() for f in formats if f and str(f).strip()]
    if not fmt_list:
        raise CorpusError("formats must include at least one entry (e.g. pdf)")
    unsupported = [f for f in fmt_list if f != "pdf"]
    if unsupported:
        raise CorpusError(
            f"Unsupported update formats: {unsupported}; only 'pdf' is supported"
        )
    repo_key = (repository or DEFAULT_REPOSITORY).strip().lower()
    if repo_key != "europe_pmc":
        raise CorpusError(
            f"Unsupported repository {repository!r}; only 'europe_pmc' for PDF update"
        )

    bag_summary = load_bagit_corpus(corpus_dir, write_review_if_missing=False)
    all_ids = list(bag_summary.get("paper_ids") or [])
    if paper_ids is not None:
        wanted = set(paper_ids)
        selected = [pid for pid in all_ids if pid in wanted]
        missing = wanted - set(selected)
        if missing:
            raise CorpusError(
                f"Unknown paper_id(s) for this corpus: {', '.join(sorted(missing))}"
            )
    else:
        selected = all_ids
    if not selected:
        raise CorpusError(f"No papers found in corpus: {corpus_dir}")

    pdf_dir = documents_dir_for_format(bag_root, "pdf")
    details: List[Dict[str, Any]] = []
    downloaded = 0
    skipped = 0
    failed = 0
    replaced_invalid = 0

    for i, paper_id in enumerate(selected):
        dest = pdf_path_for_paper(bag_root, paper_id)
        status = "pending"
        error = None
        pmcid = pmcid_from_paper_id(paper_id)

        try:
            if dest.is_file() and not is_valid_pdf(dest, min_bytes=min_pdf_bytes):
                # Remove HTML/error stubs so they can be replaced
                dest.unlink(missing_ok=True)
                replaced_invalid += 1

            if (
                not force
                and is_valid_pdf(dest, min_bytes=min_pdf_bytes)
            ):
                status = "skipped"
                skipped += 1
            else:
                if not pmcid:
                    raise CorpusError(
                        f"Cannot derive PMCID from paper_id {paper_id!r}"
                    )
                _download_europe_pmc_pdf(pmcid, dest)
                if not is_valid_pdf(dest, min_bytes=min_pdf_bytes):
                    if dest.is_file():
                        dest.unlink(missing_ok=True)
                    raise RepositoryError(
                        f"Post-download validation failed for {paper_id}"
                    )
                status = "downloaded"
                downloaded += 1
        except (CorpusError, RepositoryError, OSError) as exc:
            status = "failed"
            error = str(getattr(exc, "message", None) or exc)
            failed += 1
            if dest.is_file() and not is_valid_pdf(dest, min_bytes=min_pdf_bytes):
                dest.unlink(missing_ok=True)

        details.append(
            {
                "paper_id": paper_id,
                "pmcid": pmcid,
                "status": status,
                "path": str(dest) if dest.is_file() else None,
                "error": error,
            }
        )
        if progress_callback is not None:
            progress_callback(i + 1, len(selected), paper_id, status)

    # Refresh BAGIT checksums when possible
    manifest_updated = False
    try:
        corpus = CorpusManager(bag_root, use_bagit=True)
        if corpus.bagit_manager is not None:
            corpus.bagit_manager.update_manifest()
            manifest_updated = True
    except Exception:
        manifest_updated = False

    review_path = _refresh_review_has_pdf(corpus_dir, bag_root, selected)

    return {
        "step": "update_corpus",
        "corpus_dir": str(corpus_dir.resolve()),
        "bag_root": str(bag_root.resolve()),
        "pdf_dir": str(pdf_dir.resolve()),
        "repository": repo_key,
        "formats": fmt_list,
        "force": force,
        "paper_count": len(selected),
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "replaced_invalid": replaced_invalid,
        "manifest_updated": manifest_updated,
        "review_table": str(review_path.resolve()) if review_path else None,
        "papers": details,
    }
