"""Ingest classic pygetpapers output directories into a semantic_corpus."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.tools.metadata_processor import MetadataProcessor


def _eupmc_json_to_raw_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build raw metadata dict from Europe PMC eupmc_result.json for normalization."""
    raw: Dict[str, Any] = {}
    raw["title"] = data.get("title") or ""
    raw["abstract"] = data.get("abstractText") or ""
    raw["doi"] = data.get("doi") or ""
    raw["pmcid"] = data.get("pmcid") or ""
    raw["pmid"] = data.get("pmid") or ""
    author_string = data.get("authorString") or ""
    raw["authors"] = [
        a.strip().rstrip(".").strip()
        for a in author_string.split(",")
        if a.strip()
    ]
    raw["publication_date"] = (
        data.get("firstPublicationDate")
        or data.get("dateOfCreation")
        or (str(data.get("pubYear", "")) if data.get("pubYear") else "")
    )
    journal_info = data.get("journalInfo") or {}
    journal = journal_info.get("journal") if isinstance(journal_info.get("journal"), dict) else None
    raw["journal"] = journal.get("title", "") if journal else ""
    return raw


def _discover_paper_folders(pygetpapers_dir: Path) -> List[Path]:
    """Return list of per-article directories (e.g. PMC12345) under pygetpapers_dir."""
    if not pygetpapers_dir.is_dir():
        return []
    folders: List[Path] = []
    for child in pygetpapers_dir.iterdir():
        if child.is_dir() and child.name.startswith("PMC"):
            # Must have at least eupmc_result.json to be a paper folder
            if (child / "eupmc_result.json").exists():
                folders.append(child)
    return sorted(folders)


def ingest_pygetpapers_directory(
    pygetpapers_dir: Path,
    corpus: CorpusManager,
    paper_id_prefix: str = "europe_pmc_",
) -> List[str]:
    """Ingest a classic pygetpapers output directory into a corpus.

    Expects directory layout:
      - eupmc_results.json (optional run-level metadata)
      - PMC<id>/eupmc_result.json, fulltext.xml, and optionally fulltext.pdf

    Args:
        pygetpapers_dir: Path to the pygetpapers output directory.
        corpus: CorpusManager (BAGIT) to ingest into; create_structured_directories() must already have been called.
        paper_id_prefix: Prefix for corpus paper IDs (default "europe_pmc_").

    Returns:
        List of corpus paper IDs that were added.

    Raises:
        CorpusError: If the directory is invalid or ingestion fails.
    """
    pygetpapers_dir = Path(pygetpapers_dir)
    if not pygetpapers_dir.exists():
        raise CorpusError(f"Pygetpapers directory does not exist: {pygetpapers_dir}")
    if not pygetpapers_dir.is_dir():
        raise CorpusError(f"Not a directory: {pygetpapers_dir}")

    if not corpus.use_bagit:
        raise CorpusError("Pygetpapers ingestion requires a BAGIT corpus (use_bagit=True)")

    processor = MetadataProcessor()
    added: List[str] = []

    for paper_folder in _discover_paper_folders(pygetpapers_dir):
        pmcid = paper_folder.name
        corpus_id = f"{paper_id_prefix}{pmcid}"

        json_path = paper_folder / "eupmc_result.json"
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                eupmc_data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise CorpusError(f"Cannot read {json_path}: {e}") from e

        raw = _eupmc_json_to_raw_metadata(eupmc_data)
        normalized = processor.normalize_metadata(raw)
        corpus.add_paper(corpus_id, normalized)

        # Copy fulltext.xml to data/documents/xml/
        xml_src = paper_folder / "fulltext.xml"
        if xml_src.exists():
            xml_dst = Path(
                corpus.corpus_dir,
                "data",
                "documents",
                "xml",
                f"{corpus_id}.xml",
            )
            xml_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(xml_src, xml_dst)

        # Copy fulltext.pdf to data/documents/pdf/ if present
        pdf_src = paper_folder / "fulltext.pdf"
        if pdf_src.exists():
            pdf_dst = Path(
                corpus.corpus_dir,
                "data",
                "documents",
                "pdf",
                f"{corpus_id}.pdf",
            )
            pdf_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_src, pdf_dst)

        if corpus.bagit_manager:
            corpus.bagit_manager.update_manifest()

        added.append(corpus_id)

    return added
