"""Ingest a local directory of PDF files into a semantic_corpus."""

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Set

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.tools.metadata_processor import MetadataProcessor


def _safe_id(stem: str) -> str:
    """Turn a file name stem into a filesystem-safe corpus ID fragment."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return safe or "paper"


def _sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_pdf(path: Path) -> bool:
    """Return True if the file starts with the PDF magic bytes."""
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except OSError:
        return False


def _discover_pdfs(pdf_dir: Path, recursive: bool) -> List[Path]:
    """Return PDF files (any extension case) under pdf_dir."""
    candidates = pdf_dir.rglob("*") if recursive else pdf_dir.iterdir()
    return sorted(p for p in candidates if p.is_file() and p.suffix.lower() == ".pdf")


def _existing_hashes(metadata_dir: Path) -> Set[str]:
    """Return SHA-256 hashes of PDFs already recorded in the corpus metadata."""
    hashes: Set[str] = set()
    if not metadata_dir.is_dir():
        return hashes
    for metadata_file in metadata_dir.glob("*_metadata.json"):
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                sha = json.load(f).get("sha256")
        except (OSError, json.JSONDecodeError):
            continue
        if sha:
            hashes.add(sha)
    return hashes


def ingest_local_pdf_directory(
    pdf_dir: Path,
    corpus: CorpusManager,
    paper_id_prefix: str = "local_",
    recursive: bool = False,
) -> Dict[str, Any]:
    """Ingest a directory of local PDF files into a corpus.

    Each PDF is copied to data/documents/pdf/{corpus_id}.pdf and its metadata
    (embedded PDF title/author if available, plus provenance) is written to
    data/metadata/{corpus_id}_metadata.json. PDFs whose content is already in
    the corpus (same SHA-256) are skipped, so re-running an import is safe.

    Args:
        pdf_dir: Directory containing PDF files.
        corpus: CorpusManager (BAGIT) to ingest into.
        paper_id_prefix: Prefix for corpus paper IDs (default "local_").
        recursive: Also search subdirectories of pdf_dir.

    Returns:
        Dict with "added" (corpus IDs), "duplicates" and "skipped"
        (lists of {"path", "reason"} for files that were not imported).

    Raises:
        CorpusError: If the directory or corpus is invalid.
    """
    pdf_dir = Path(pdf_dir)
    if not pdf_dir.exists():
        raise CorpusError(f"PDF directory does not exist: {pdf_dir}")
    if not pdf_dir.is_dir():
        raise CorpusError(f"Not a directory: {pdf_dir}")
    if not corpus.use_bagit:
        raise CorpusError(
            "Local PDF ingestion requires a BAGIT corpus (use_bagit=True)"
        )

    pdf_dst_dir = Path(corpus.corpus_dir, "data", "documents", "pdf")
    pdf_dst_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir = Path(corpus.corpus_dir, "data", "metadata")
    metadata_dir.mkdir(parents=True, exist_ok=True)

    processor = MetadataProcessor()
    seen_hashes = _existing_hashes(metadata_dir)
    added: List[str] = []
    duplicates: List[Dict[str, str]] = []
    skipped: List[Dict[str, str]] = []

    for pdf_src in _discover_pdfs(pdf_dir, recursive):
        if not _is_pdf(pdf_src):
            skipped.append({"path": str(pdf_src), "reason": "not a valid PDF"})
            continue

        try:
            sha = _sha256(pdf_src)
        except OSError as e:
            skipped.append({"path": str(pdf_src), "reason": str(e)})
            continue
        if sha in seen_hashes:
            duplicates.append({"path": str(pdf_src), "reason": "already in corpus"})
            continue

        base_id = f"{paper_id_prefix}{_safe_id(pdf_src.stem)}"
        corpus_id = base_id
        suffix = 2
        while (pdf_dst_dir / f"{corpus_id}.pdf").exists() or Path(
            metadata_dir, f"{corpus_id}_metadata.json"
        ).exists():
            corpus_id = f"{base_id}_{suffix}"
            suffix += 1

        try:
            raw = processor.process_pdf_metadata(pdf_src)
        except Exception as e:  # metadata is best-effort; keep the PDF
            raw = {"file_type": "pdf", "metadata_error": str(e)}

        # Provenance; file_path would otherwise point outside the corpus
        raw.pop("file_path", None)
        raw.setdefault("title", "")
        if not raw["title"].strip():
            raw["title"] = pdf_src.stem
        raw.update(
            {
                "source": "local",
                "original_path": str(pdf_src.resolve()),
                "original_filename": pdf_src.name,
                "sha256": sha,
            }
        )

        try:
            shutil.copy2(pdf_src, pdf_dst_dir / f"{corpus_id}.pdf")
        except OSError as e:
            skipped.append({"path": str(pdf_src), "reason": str(e)})
            continue

        # Same file as corpus.add_paper(), which would also rehash the whole
        # bag for every paper; the manifest is updated once below instead.
        metadata_file = metadata_dir / f"{corpus_id}_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(
                processor.normalize_metadata(raw), f, indent=2, ensure_ascii=False
            )
        seen_hashes.add(sha)
        added.append(corpus_id)

    if corpus.bagit_manager:
        corpus.bagit_manager.update_manifest()

    return {"added": added, "duplicates": duplicates, "skipped": skipped}
