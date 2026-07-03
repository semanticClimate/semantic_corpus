"""Build and export corpus review tables for browsing."""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.constants import REVIEW_TABLE_COLUMNS
from semantic_corpus.corpus_review.query_run import load_query_run_record
from semantic_corpus.corpus_review.relevance_scorer import score_paper_relevance
from semantic_corpus.corpus_review.review_schema import make_review_row
from semantic_corpus.ingestion.pygetpapers_ingester import (
    _discover_paper_folders,
    _eupmc_json_to_raw_metadata,
)
from semantic_corpus.tools.metadata_processor import MetadataProcessor


def _paper_file_path(corpus_dir: Path, paper_id: str, ext: str) -> Path:
    sub = "xml" if ext == "xml" else "pdf"
    return Path(corpus_dir, "data", "documents", sub, f"{paper_id}.{ext}")


def _paper_has_file(corpus_dir: Path, paper_id: str, ext: str) -> bool:
    path = _paper_file_path(corpus_dir, paper_id, ext)
    return path.is_file() and path.stat().st_size > 0


def build_review_rows_from_corpus(
    corpus: CorpusManager,
    *,
    query_name: str = "",
    query_string: str = "",
) -> List[Dict[str, Any]]:
    """Build review rows from an ingested BAGIT corpus."""
    if not corpus.use_bagit:
        raise CorpusError("Review table requires BAGIT corpus (use_bagit=True)")

    rows: List[Dict[str, Any]] = []
    for paper_id in sorted(corpus.list_papers()):
        metadata = corpus.get_paper_metadata(paper_id)
        has_xml = _paper_has_file(corpus.corpus_dir, paper_id, "xml")
        has_pdf = _paper_has_file(corpus.corpus_dir, paper_id, "pdf")
        pdf_path = (
            str(_paper_file_path(corpus.corpus_dir, paper_id, "pdf"))
            if has_pdf
            else ""
        )
        score, matched = score_paper_relevance(
            metadata, has_xml=has_xml, has_pdf=has_pdf
        )
        rows.append(
            make_review_row(
                paper_id=paper_id,
                metadata=metadata,
                score=score,
                location_terms=matched["location_terms"],
                pollutant_terms=matched["pollutant_terms"],
                health_terms=matched["health_terms"],
                has_xml=has_xml,
                has_pdf=has_pdf,
                pdf_path=pdf_path,
                query_name=query_name,
                query_string=query_string,
            )
        )
    rows.sort(key=lambda r: (-int(r["score"]), r["paper_id"]))
    return rows


def build_review_rows_from_pygetpapers(
    pygetpapers_dir: Path,
    *,
    query_name: str = "",
    query_string: str = "",
) -> List[Dict[str, Any]]:
    """Build review rows from raw pygetpapers output (before or without corpus ingest)."""
    pygetpapers_dir = Path(pygetpapers_dir)
    processor = MetadataProcessor()
    rows: List[Dict[str, Any]] = []

    for folder in _discover_paper_folders(pygetpapers_dir):
        json_path = Path(folder, "eupmc_result.json")
        with open(json_path, "r", encoding="utf-8") as handle:
            eupmc_data = json.load(handle)
        raw = _eupmc_json_to_raw_metadata(eupmc_data)
        metadata = processor.normalize_metadata(raw)
        paper_id = f"europe_pmc_{folder.name}"
        has_xml = Path(folder, "fulltext.xml").is_file()
        pdf_file = Path(folder, "fulltext.pdf")
        has_pdf = pdf_file.is_file()
        pdf_path = str(pdf_file) if has_pdf else ""
        score, matched = score_paper_relevance(
            metadata, has_xml=has_xml, has_pdf=has_pdf
        )
        rows.append(
            make_review_row(
                paper_id=paper_id,
                metadata=metadata,
                score=score,
                location_terms=matched["location_terms"],
                pollutant_terms=matched["pollutant_terms"],
                health_terms=matched["health_terms"],
                has_xml=has_xml,
                has_pdf=has_pdf,
                pdf_path=pdf_path,
                query_name=query_name,
                query_string=query_string,
            )
        )
    rows.sort(key=lambda r: (-int(r["score"]), r["paper_id"]))
    return rows


def _normalize_author_names(authors: Any) -> List[str]:
    """Flatten Europe PMC author entries (dicts or strings) into name strings."""
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


def build_review_rows_from_search_results(
    search_results_path: Path,
    *,
    xml_dir: Optional[Path] = None,
    query_name: str = "",
    query_string: str = "",
) -> List[Dict[str, Any]]:
    """Build review rows from a flat semantic_corpus search_results.json.

    Layout: search_results.json (list of paper dicts) plus optional sibling
    {pmcid}.xml / {pmcid}.pdf files (as produced by the download workflow).

    Args:
        search_results_path: Path to search_results.json.
        xml_dir: Directory holding {pmcid}.xml/.pdf; defaults to the JSON's folder.
        query_name: Query name for provenance columns.
        query_string: Query string for provenance columns.

    Returns:
        Review rows sorted by descending score.
    """
    search_results_path = Path(search_results_path)
    if not search_results_path.is_file():
        raise CorpusError(f"search_results.json not found: {search_results_path}")

    if xml_dir is None:
        xml_dir = search_results_path.parent
    xml_dir = Path(xml_dir)

    with open(search_results_path, "r", encoding="utf-8") as handle:
        results = json.load(handle)
    if not isinstance(results, list):
        raise CorpusError(
            f"search_results.json must contain a list, got {type(results).__name__}"
        )

    rows: List[Dict[str, Any]] = []
    for paper in results:
        pmcid = paper.get("pmcid") or ""
        pmid = paper.get("pmid") or ""
        identifier = pmcid or pmid
        paper_id = f"europe_pmc_{identifier}" if identifier else "europe_pmc_unknown"

        has_xml = bool(pmcid) and Path(xml_dir, f"{pmcid}.xml").is_file()
        pdf_file = Path(xml_dir, f"{pmcid}.pdf")
        has_pdf = bool(pmcid) and pdf_file.is_file()
        pdf_path = str(pdf_file) if has_pdf else ""

        metadata = dict(paper)
        metadata["authors"] = _normalize_author_names(paper.get("authors"))

        score, matched = score_paper_relevance(
            metadata, has_xml=has_xml, has_pdf=has_pdf
        )
        rows.append(
            make_review_row(
                paper_id=paper_id,
                metadata=metadata,
                score=score,
                location_terms=matched["location_terms"],
                pollutant_terms=matched["pollutant_terms"],
                health_terms=matched["health_terms"],
                has_xml=has_xml,
                has_pdf=has_pdf,
                pdf_path=pdf_path,
                query_name=query_name,
                query_string=query_string,
            )
        )
    rows.sort(key=lambda r: (-int(r["score"]), r["paper_id"]))
    return rows


def export_review_table_json(rows: List[Dict[str, Any]], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)
    return path


def export_review_table_csv(rows: List[Dict[str, Any]], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REVIEW_TABLE_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in REVIEW_TABLE_COLUMNS})
    return path


def export_review_table_markdown(rows: List[Dict[str, Any]], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Corpus review table",
        "",
        "| review_status | score | title | pmcid | cluster | encyclopedia | pdf |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        title = (row["title"] or "").replace("|", "\\|")[:80]
        pdf_path = row.get("pdf_path") or ""
        pdf_cell = f"[PDF]({pdf_path})" if pdf_path else ""
        cluster = row.get("cluster_id", "")
        encyclopedia = row.get("encyclopedia_category", "")
        lines.append(
            f"| {row['review_status']} | {row['score']} | {title} | "
            f"{row['pmcid']} | {cluster} | {encyclopedia} | {pdf_cell} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def export_review_tables(
    rows: List[Dict[str, Any]], output_dir: Path, basename: str = "review_table"
) -> Dict[str, Path]:
    """Export JSON, CSV, and Markdown review tables."""
    output_dir = Path(output_dir)
    return {
        "json": export_review_table_json(
            rows, Path(output_dir, f"{basename}.json")
        ),
        "csv": export_review_table_csv(rows, Path(output_dir, f"{basename}.csv")),
        "markdown": export_review_table_markdown(
            rows, Path(output_dir, f"{basename}.md")
        ),
    }


def load_query_context(query_run_path: Optional[Path]) -> Dict[str, str]:
    if not query_run_path or not Path(query_run_path).is_file():
        return {"query_name": "", "query_string": ""}
    record = load_query_run_record(query_run_path)
    return {
        "query_name": record.get("query_name") or "",
        "query_string": record.get("query_string") or "",
    }
