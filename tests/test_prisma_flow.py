"""Tests for PRISMA-like flow counts and diagram rendering."""

import json
from pathlib import Path

import pytest
import yaml

from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.prisma_diagram import (
    render_prisma_mermaid,
    write_prisma_diagrams,
)
from semantic_corpus.corpus_review.prisma_flow import (
    build_prisma_flow,
    default_prisma_output_dir,
    validate_prisma_flow,
    write_prisma_flow_json,
)


def _write_review_table(path: Path, rows: list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return path


def _sample_rows():
    return [
        {
            "review_status": "include",
            "has_xml": True,
            "has_pdf": True,
            "query_name": "climate_pilot",
            "query_string": "climate change",
        },
        {
            "review_status": "exclude",
            "has_xml": True,
            "has_pdf": False,
            "query_name": "climate_pilot",
            "query_string": "climate change",
        },
        {
            "review_status": "review",
            "has_xml": False,
            "has_pdf": False,
            "query_name": "climate_pilot",
            "query_string": "climate change",
        },
        {
            "review_status": "review",
            "has_xml": True,
            "has_pdf": True,
            "query_name": "climate_pilot",
            "query_string": "climate change",
        },
    ]


class TestPrismaFlow:
    def test_counts_and_overrides(self, tmp_path: Path) -> None:
        review_path = _write_review_table(
            Path(tmp_path, "review", "review_table.json"),
            _sample_rows(),
        )
        query_run = Path(tmp_path, "query_run.json")
        query_run.write_text(
            json.dumps(
                {
                    "query_name": "climate_pilot",
                    "query_string": "climate change",
                    "repository": "europe_pmc",
                    "limit": 4,
                    "result_count": 4,
                    "downloaded_count": 3,
                    "formats": ["xml", "pdf"],
                }
            ),
            encoding="utf-8",
        )
        overrides = Path(tmp_path, "prisma_overrides.yaml")
        overrides.write_text(
            yaml.safe_dump(
                {
                    "n_identified": 100,
                    "notes": "Hit count from Europe PMC UI (system date test)",
                }
            ),
            encoding="utf-8",
        )

        flow = build_prisma_flow(
            query_run_path=query_run,
            review_table_path=review_path,
            overrides_path=overrides,
            corpus_dir=Path(tmp_path, "corpus"),
        )
        counts = flow["counts"]
        assert counts["n_identified"] == 100, (
            f"Expected overridden n_identified=100, got {counts['n_identified']}"
        )
        assert flow["meta"]["identified_source"] == "overrides.n_identified"
        assert flow["meta"]["identified_is_hitcount"] is True
        assert counts["n_beyond_limit"] == 96, (
            f"Expected n_beyond_limit=96, got {counts['n_beyond_limit']}"
        )
        roles = {item["role"] for item in flow["artefacts"]}
        assert "raw_query" in roles
        assert "review_table" in roles
        assert "query_run" in roles
        assert counts["n_retrieved"] == 4
        assert counts["n_screened"] == 4
        assert counts["n_include"] == 1
        assert counts["n_exclude"] == 1
        assert counts["n_still_review"] == 2
        assert counts["n_final_table"] == 3, (
            "Final table must include + still_review (1+2=3)"
        )
        assert counts["n_with_fulltext"] == 3
        validate_prisma_flow(flow)

    def test_mermaid_mentions_still_review_and_artefacts(self, tmp_path: Path) -> None:
        review_path = _write_review_table(
            Path(tmp_path, "review_table.json"),
            _sample_rows(),
        )
        query_run = Path(tmp_path, "query_run.json")
        query_run.write_text(
            json.dumps(
                {
                    "query_name": "climate_pilot",
                    "query_string": "climate change AND adaptation",
                    "repository": "europe_pmc",
                    "limit": 4,
                    "result_count": 4,
                }
            ),
            encoding="utf-8",
        )
        flow = build_prisma_flow(
            review_table_path=review_path,
            query_run_path=query_run,
            query_dir=tmp_path,
            repo_root=tmp_path,
        )
        mermaid = render_prisma_mermaid(flow)
        assert "still review" in mermaid.lower(), (
            "Mermaid diagram should show still review count"
        )
        assert "FINAL TABLE" in mermaid
        assert "raw query" in mermaid.lower()
        assert "Local artefacts" in mermaid
        assert "NOT a database hitCount" in mermaid
        paths = write_prisma_diagrams(flow, Path(tmp_path, "prisma"))
        json_path = write_prisma_flow_json(flow, Path(tmp_path, "prisma"))
        assert paths["mermaid"].is_file()
        assert paths["dot"].is_file()
        assert json_path.is_file()
        assert "digraph" in paths["dot"].read_text(encoding="utf-8")
        assert "Local artefacts" in paths["dot"].read_text(encoding="utf-8")

    def test_default_output_under_corpus_analysis(self, tmp_path: Path) -> None:
        corpus_dir = Path(tmp_path, "corpora", "climate_pilot")
        out = default_prisma_output_dir(corpus_dir)
        assert out == Path(corpus_dir, "data", "analysis", "prisma")

    def test_status_invariant_failure(self) -> None:
        with pytest.raises(CorpusError):
            validate_prisma_flow(
                {
                    "counts": {
                        "n_screened": 3,
                        "n_include": 1,
                        "n_exclude": 0,
                        "n_still_review": 0,
                        "n_final_table": 1,
                    }
                }
            )
