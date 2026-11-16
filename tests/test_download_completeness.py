"""Tests for download completeness hard check."""

import json
from pathlib import Path

from semantic_corpus.corpus_review.constants import (
    DOWNLOAD_INCOMPLETE_PREFIX,
    DOWNLOAD_STATUS_COMPLETE,
    DOWNLOAD_STATUS_INCOMPLETE,
)
from semantic_corpus.corpus_review.download_completeness import (
    check_download_completeness,
)
from semantic_corpus.corpus_review.prisma_flow import build_prisma_flow


def test_download_complete_when_all_formats_present(tmp_path: Path) -> None:
    papers = [
        {"pmcid": "PMC1", "pmid": "1", "title": "A"},
        {"pmcid": "PMC2", "pmid": "2", "title": "B"},
    ]
    for paper in papers:
        Path(tmp_path, f"{paper['pmcid']}.xml").write_text("<xml/>", encoding="utf-8")
        Path(tmp_path, f"{paper['pmcid']}.pdf").write_bytes(b"%PDF")
    result = check_download_completeness(
        query_dir=tmp_path,
        papers=papers,
        formats=["xml", "pdf"],
    )
    assert result["status"] == DOWNLOAD_STATUS_COMPLETE
    assert result["complete"] is True
    assert result["n_present_files"] == 4
    assert "DOWNLOAD COMPLETE" in result["message"]


def test_download_incomplete_message(tmp_path: Path) -> None:
    papers = [
        {"pmcid": "PMC1", "pmid": "1", "title": "Has xml only"},
        {"pmcid": "", "pmid": "99", "title": "Missing all"},
    ]
    Path(tmp_path, "PMC1.xml").write_text("<xml/>", encoding="utf-8")
    result = check_download_completeness(
        query_dir=tmp_path,
        papers=papers,
        formats=["xml", "pdf"],
        downloaded_count=1,
    )
    assert result["status"] == DOWNLOAD_STATUS_INCOMPLETE
    assert result["complete"] is False
    assert result["n_expected_files"] == 4
    assert result["n_present_files"] == 1
    assert result["n_missing_files"] == 3
    assert result["message"].startswith(DOWNLOAD_INCOMPLETE_PREFIX)


def test_prisma_flow_includes_download_check(tmp_path: Path) -> None:
    query_dir = Path(tmp_path, "query")
    query_dir.mkdir()
    papers = [{"pmcid": "PMC9", "pmid": "9", "title": "T", "doi": "10.1/x"}]
    Path(query_dir, "search_results.json").write_text(
        json.dumps(papers), encoding="utf-8"
    )
    Path(query_dir, "query_run.json").write_text(
        json.dumps(
            {
                "query_name": "climate_pilot",
                "query_string": "climate change",
                "repository": "europe_pmc",
                "limit": 1,
                "formats": ["xml", "pdf"],
                "result_count": 1,
                "downloaded_count": 0,
            }
        ),
        encoding="utf-8",
    )
    review = [
        {
            "review_status": "review",
            "has_xml": False,
            "has_pdf": False,
            "query_name": "climate_pilot",
            "query_string": "climate change",
            "pmcid": "PMC9",
        }
    ]
    review_path = Path(query_dir, "review", "review_table.json")
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(review), encoding="utf-8")

    flow = build_prisma_flow(
        query_run_path=Path(query_dir, "query_run.json"),
        review_table_path=review_path,
        search_results_path=Path(query_dir, "search_results.json"),
        query_dir=query_dir,
        repo_root=tmp_path,
    )
    check = flow["download_check"]
    assert check["status"] == DOWNLOAD_STATUS_INCOMPLETE
    assert check["message"].startswith(DOWNLOAD_INCOMPLETE_PREFIX)
    assert flow["counts"]["n_download_failed"] == 2
