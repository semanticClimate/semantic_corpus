"""End-to-end AQI corpus review workflow helpers."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.corpus_review.query_run import (
    build_query_run_record,
    load_pilot_config,
    save_query_run_record,
    summarize_query_run,
)
from semantic_corpus.corpus_review.review_table import (
    build_review_rows_from_corpus,
    build_review_rows_from_pygetpapers,
    build_review_rows_from_search_results,
    export_review_tables,
    load_query_context,
)
from semantic_corpus.export.chatbot_export import export_corpus_for_chatbot
from semantic_corpus.ingestion.pygetpapers_ingester import ingest_pygetpapers_directory
from semantic_corpus.utils import get_project_temp_dir


def run_repository_search(
    *,
    query_string: str,
    repository: str,
    limit: int,
    output_dir: Path,
    formats: List[str],
) -> Tuple[List[Dict[str, Any]], int]:
    """Search and download via semantic_corpus repository; return results and download count."""
    repo = RepositoryFactory.get_repository(repository)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = repo.search_papers(query=query_string, limit=limit)
    downloaded_count = 0
    for paper in results:
        paper_id = paper.get("pmcid") or paper.get("pmid")
        if not paper_id:
            continue
        try:
            dl = repo.download_paper(paper_id, output_dir, formats)
            if dl.get("success"):
                downloaded_count += 1
        except Exception:
            continue
    return results, downloaded_count


def run_query_and_build_review_table(
    *,
    query_name: str,
    query_string: str,
    output_dir: Path,
    repository: str = "europe_pmc",
    limit: int = 25,
    formats: List[str] = None,
    notes: str = "",
    revision_of: str = None,
) -> Dict[str, Any]:
    """Search, download, and build review table under an explicit output directory.

    Suitable for Colab or any environment where output should not go under
    the repo temp/ tree.

    Args:
        query_name: Short name for this query run.
        query_string: Europe PMC query string.
        output_dir: Directory for search_results.json, downloads, and review/.
        repository: Repository key (default europe_pmc).
        limit: Maximum papers to retrieve.
        formats: Download formats (default xml).
        notes: Optional free-text notes stored in query_run.json.
        revision_of: Optional prior query_name when refining a query.

    Returns:
        Summary dict with counts, paths, rows, and query run record.
    """
    output_dir = Path(output_dir)
    if formats is None:
        formats = ["xml"]

    results, downloaded_count = run_repository_search(
        query_string=query_string,
        repository=repository,
        limit=limit,
        output_dir=output_dir,
        formats=formats,
    )

    results_path = Path(output_dir, "search_results.json")
    with open(results_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)

    record = build_query_run_record(
        query_name=query_name,
        query_string=query_string,
        repository=repository,
        limit=limit,
        formats=formats,
        output_dir=output_dir,
        result_count=len(results),
        downloaded_count=downloaded_count,
        notes=notes,
        revision_of=revision_of,
    )
    query_run_path = save_query_run_record(record, output_dir)

    rows = build_review_rows_from_search_results(
        results_path,
        xml_dir=output_dir,
        query_name=query_name,
        query_string=query_string,
    )
    review_paths = export_review_tables(rows, Path(output_dir, "review"))

    high_score_count = sum(1 for row in rows if int(row["score"]) >= 5)
    xml_count = sum(1 for row in rows if row["has_xml"])

    return {
        "query_name": query_name,
        "query_string": query_string,
        "result_count": len(results),
        "downloaded_count": downloaded_count,
        "row_count": len(rows),
        "high_score_count": high_score_count,
        "xml_count": xml_count,
        "output_dir": str(output_dir),
        "search_results_path": str(results_path),
        "query_run_path": str(query_run_path),
        "review_paths": {k: str(v) for k, v in review_paths.items()},
        "rows": rows,
        "query_run": record,
        "summary": summarize_query_run(record),
    }


def review_rows_to_dataframe(rows: List[Dict[str, Any]]):
    """Convert review rows to a pandas DataFrame (requires pandas)."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise CorpusError(
            "pandas is required for review_rows_to_dataframe; install with: pip install pandas"
        ) from exc
    return pd.DataFrame(rows)


def run_pilot_from_config(config_path: Path) -> Dict[str, Any]:
    """Run pilot query from YAML config; write query_run.json and search_results.json."""
    config = load_pilot_config(config_path)
    output_dir = Path(
        get_project_temp_dir(),
        "queries",
        config.get("output_subdir") or config["query_name"],
    )
    formats = config.get("formats") or ["xml"]
    results, downloaded_count = run_repository_search(
        query_string=config["query_string"],
        repository=config.get("repository") or "europe_pmc",
        limit=int(config.get("limit") or 25),
        output_dir=output_dir,
        formats=formats,
    )

    results_path = Path(output_dir, "search_results.json")
    with open(results_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)

    record = build_query_run_record(
        query_name=config["query_name"],
        query_string=config["query_string"],
        repository=config.get("repository") or "europe_pmc",
        limit=int(config.get("limit") or 25),
        formats=formats,
        output_dir=output_dir,
        result_count=len(results),
        downloaded_count=downloaded_count,
    )
    save_query_run_record(record, output_dir)
    record["summary"] = summarize_query_run(record)
    record["search_results_path"] = str(results_path)
    return record


def ingest_and_review_pygetpapers(
    pygetpapers_dir: Path,
    corpus_dir: Path,
    *,
    query_run_path: Path = None,
) -> Dict[str, Path]:
    """Ingest pygetpapers dir into BAGIT corpus and export review tables."""
    ctx = load_query_context(query_run_path)
    corpus = CorpusManager(Path(corpus_dir), use_bagit=True)
    corpus.create_structured_directories()
    ingest_pygetpapers_directory(Path(pygetpapers_dir), corpus)
    rows = build_review_rows_from_corpus(
        corpus,
        query_name=ctx["query_name"],
        query_string=ctx["query_string"],
    )
    review_dir = Path(corpus.corpus_dir, "analysis", "review")
    return export_review_tables(rows, review_dir)


def export_reviewed_corpus_for_chatbot(
    corpus_dir: Path,
    export_dir: Path,
    *,
    review_table_path: Path = None,
) -> Path:
    """Export chatbot manifest using review table include status when provided."""
    corpus = CorpusManager(Path(corpus_dir), use_bagit=True)
    review_rows = None
    if review_table_path and Path(review_table_path).is_file():
        with open(review_table_path, "r", encoding="utf-8") as handle:
            review_rows = json.load(handle)
    return export_corpus_for_chatbot(
        corpus,
        Path(export_dir),
        review_rows=review_rows,
        include_only_status=True,
    )
