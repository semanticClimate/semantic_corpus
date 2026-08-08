"""Ingest flat query output (search_results.json + downloaded files) into a corpus."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.tools.metadata_processor import MetadataProcessor


def _normalize_author_names(authors: Any) -> List[str]:
    if not authors:
        return []
    if isinstance(authors, str):
        return [authors]
    names: List[str] = []
    for author in authors:
        if isinstance(author, dict):
            name = (
                author.get("fullName")
                or author.get("lastName")
                or author.get("firstName")
                or ""
            )
            if name:
                names.append(str(name))
        elif author:
            names.append(str(author))
    return names


def ingest_query_output_directory(
    query_dir: Path,
    corpus: CorpusManager,
    *,
    search_results_path: Path = None,
    paper_id_prefix: str = "europe_pmc_",
) -> List[str]:
    """Ingest a flat query directory into a BAGIT corpus.

    Expects:
      - search_results.json (list of paper metadata dicts)
      - {pmcid}.xml and/or {pmcid}.pdf alongside the JSON

    Args:
        query_dir: Directory containing search results and downloads.
        corpus: BAGIT CorpusManager with structured directories created.
        search_results_path: Optional explicit path to search_results.json.
        paper_id_prefix: Prefix for corpus paper IDs.

    Returns:
        List of corpus paper IDs added.
    """
    query_dir = Path(query_dir)
    if not query_dir.is_dir():
        raise CorpusError(f"Query directory not found: {query_dir}")
    if not corpus.use_bagit:
        raise CorpusError("Query ingestion requires BAGIT corpus (use_bagit=True)")

    results_path = Path(search_results_path) if search_results_path else Path(query_dir, "search_results.json")
    if not results_path.is_file():
        raise CorpusError(f"search_results.json not found: {results_path}")

    with open(results_path, "r", encoding="utf-8") as handle:
        results = json.load(handle)
    if not isinstance(results, list):
        raise CorpusError("search_results.json must contain a list")

    processor = MetadataProcessor()
    added: List[str] = []

    for paper in results:
        pmcid = paper.get("pmcid") or ""
        pmid = paper.get("pmid") or ""
        identifier = pmcid or pmid
        if not identifier:
            continue

        corpus_id = f"{paper_id_prefix}{identifier}"
        raw = dict(paper)
        raw["authors"] = _normalize_author_names(paper.get("authors"))
        normalized = processor.normalize_metadata(raw)
        corpus.add_paper(corpus_id, normalized)

        if pmcid:
            xml_src = Path(query_dir, f"{pmcid}.xml")
            if xml_src.is_file():
                xml_dst = Path(
                    corpus.corpus_dir, "data", "documents", "xml", f"{corpus_id}.xml"
                )
                xml_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(xml_src, xml_dst)

            pdf_src = Path(query_dir, f"{pmcid}.pdf")
            if pdf_src.is_file():
                pdf_dst = Path(
                    corpus.corpus_dir, "data", "documents", "pdf", f"{corpus_id}.pdf"
                )
                pdf_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(pdf_src, pdf_dst)

        if corpus.bagit_manager:
            corpus.bagit_manager.update_manifest()
        added.append(corpus_id)

    return added
