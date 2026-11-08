"""Step 0: search repositories, download, review table, optional BAGIT corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.core.repository_factory import RepositoryFactory
from semantic_corpus.corpus_review.collect_progress import (
    CollectTitleScroller,
    title_from_paper,
)
from semantic_corpus.corpus_review.query_run import (
    build_query_run_record,
    save_query_run_record,
    summarize_query_run,
)
from semantic_corpus.corpus_review.review_table import (
    build_review_rows_from_search_results,
    export_review_tables,
)
from semantic_corpus.corpus_review.workflow import run_repository_search
from semantic_corpus.ingestion.query_output_ingester import (
    ingest_query_output_directory,
)
from semantic_corpus.repositories._ids import get_result_paper_id


def _as_repo_list(
    repositories: Union[str, Sequence[str]],
) -> List[str]:
    if isinstance(repositories, str):
        names = [repositories]
    else:
        names = [str(r).strip() for r in repositories if str(r).strip()]
    if not names:
        raise CorpusError("At least one repository is required")
    unknown = [n for n in names if n not in RepositoryFactory.list_repositories()]
    if unknown:
        available = ", ".join(RepositoryFactory.list_repositories())
        raise CorpusError(
            f"Unknown repository(ies): {', '.join(unknown)}. Available: {available}"
        )
    return names


def create_corpus_from_query(
    *,
    query_string: str,
    query_name: str,
    query_dir: Path,
    repositories: Union[str, Sequence[str]] = "europe_pmc",
    limit: int = 50,
    formats: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    corpus_dir: Optional[Path] = None,
    create_bagit: bool = True,
    paper_id_prefix: Optional[str] = None,
    show_title_feed: bool = True,
    check_epmc: bool = True,
    on_paper: Optional[Callable[[Dict[str, Any], str], None]] = None,
) -> Dict[str, Any]:
    """Search one or more repositories, download, build review table, optional BAGIT.

    This is Step 0 of the cluster-review UI/pipeline.

    Args:
        query_string: Repository query string.
        query_name: Short name for this run (review table + query_run provenance).
        query_dir: Directory for downloads, search_results.json, review/.
        repositories: One name or a sequence (searched in order until ``limit``
            successful downloads; later repos fill remaining slots).
        limit: Maximum papers to keep after successful download.
        formats: Download formats (default ``["xml"]``).
        start_date / end_date: Optional ISO date bounds where the adapter supports them.
        corpus_dir: BAGIT corpus root when ``create_bagit`` is True.
        create_bagit: If True, ingest query_dir into a new/updated BAGIT at corpus_dir.
        paper_id_prefix: Optional prefix for corpus IDs (default derived from first repo).
        show_title_feed: If True, show a scrolling title window while downloading.
        check_epmc: If True and Europe PMC is used, run a novice-friendly health
            check before downloading (aborts on clear EPMC outages).
        on_paper: Optional callback ``(paper, status)`` in addition to the title feed.

    Returns:
        Summary dict with paths, counts, and review rows.
    """
    if not query_string or not str(query_string).strip():
        raise CorpusError("query_string is required")
    if not query_name or not str(query_name).strip():
        raise CorpusError("query_name is required")

    repo_names = _as_repo_list(repositories)
    query_dir = Path(query_dir)
    query_dir.mkdir(parents=True, exist_ok=True)
    if formats is None:
        formats = ["xml"]

    if create_bagit:
        if corpus_dir is None:
            raise CorpusError("corpus_dir is required when create_bagit=True")
        corpus_dir = Path(corpus_dir)

    if check_epmc and "europe_pmc" in repo_names:
        from semantic_corpus.repositories.epmc_diagnostic import epmc_preflight

        epmc_preflight(abort=True)

    remaining = int(limit)
    all_results: List[Dict[str, Any]] = []
    total_downloaded = 0
    total_skipped = 0
    per_repo: List[Dict[str, Any]] = []

    scroller: Optional[CollectTitleScroller] = None
    if show_title_feed:
        scroller = CollectTitleScroller(limit=int(limit))

    def _handle_paper(
        paper: Dict[str, Any], status: str, reason: str = ""
    ) -> None:
        nonlocal total_skipped
        if status == "skip":
            total_skipped += 1
        if scroller is not None:
            scroller.add(
                title=title_from_paper(paper),
                paper_id=str(get_result_paper_id(paper) or ""),
                status=status,
                reason=reason,
            )
        if on_paper is not None:
            try:
                on_paper(paper, status, reason)
            except TypeError:
                on_paper(paper, status)

    for repo_name in repo_names:
        if remaining <= 0:
            break
        if scroller is not None:
            scroller.start(query=query_string, repository=repo_name)
        results, downloaded_count = run_repository_search(
            query_string=query_string,
            repository=repo_name,
            limit=remaining,
            output_dir=query_dir,
            formats=formats,
            start_date=start_date,
            end_date=end_date,
            on_paper=_handle_paper if (scroller is not None or on_paper) else None,
        )
        all_results.extend(results)
        total_downloaded += downloaded_count
        remaining = max(0, int(limit) - total_downloaded)
        per_repo.append(
            {
                "repository": repo_name,
                "result_count": len(results),
                "downloaded_count": downloaded_count,
            }
        )

    if scroller is not None:
        scroller.finish(downloaded=total_downloaded, skipped=total_skipped)

    # Deduplicate by pmcid/pmid/paper_id while preserving order
    seen = set()
    unique_results: List[Dict[str, Any]] = []
    for paper in all_results:
        key = (
            paper.get("paper_id")
            or paper.get("pmcid")
            or paper.get("pmid")
            or paper.get("doi")
            or id(paper)
        )
        if key in seen:
            continue
        seen.add(key)
        unique_results.append(paper)
    unique_results = unique_results[: int(limit)]

    results_path = Path(query_dir, "search_results.json")
    with open(results_path, "w", encoding="utf-8") as handle:
        json.dump(unique_results, handle, indent=2, ensure_ascii=False)

    primary_repo = repo_names[0]
    record = build_query_run_record(
        query_name=query_name,
        query_string=query_string,
        repository="+".join(repo_names),
        limit=int(limit),
        formats=formats,
        output_dir=query_dir,
        result_count=len(unique_results),
        downloaded_count=total_downloaded,
        notes=f"cluster_review step0; per_repo={per_repo}",
    )
    query_run_path = save_query_run_record(record, query_dir)

    rows = build_review_rows_from_search_results(
        results_path,
        xml_dir=query_dir,
        query_name=query_name,
        query_string=query_string,
    )
    review_paths = export_review_tables(rows, Path(query_dir, "review"))

    bagit_added: List[str] = []
    if create_bagit:
        assert corpus_dir is not None
        corpus_dir.parent.mkdir(parents=True, exist_ok=True)
        corpus = CorpusManager(corpus_dir, use_bagit=True)
        corpus.create_structured_directories()
        prefix = paper_id_prefix
        if prefix is None:
            prefix = f"{primary_repo}_"
        bagit_added = ingest_query_output_directory(
            query_dir,
            corpus,
            search_results_path=results_path,
            paper_id_prefix=prefix,
        )
        if corpus.bagit_manager:
            corpus.bagit_manager.update_manifest()

    return {
        "step": 0,
        "query_name": query_name,
        "query_string": query_string,
        "repositories": repo_names,
        "per_repo": per_repo,
        "limit": int(limit),
        "formats": formats,
        "result_count": len(unique_results),
        "downloaded_count": total_downloaded,
        "row_count": len(rows),
        "query_dir": str(query_dir.resolve()),
        "corpus_dir": str(corpus_dir.resolve()) if corpus_dir else "",
        "create_bagit": create_bagit,
        "bagit_paper_ids": bagit_added,
        "bagit_paper_count": len(bagit_added),
        "search_results_path": str(results_path.resolve()),
        "query_run_path": str(Path(query_run_path).resolve()),
        "review_paths": {k: str(Path(v).resolve()) for k, v in review_paths.items()},
        "rows": rows,
        "query_run_summary": summarize_query_run(record),
    }
