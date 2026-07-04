#!/usr/bin/env python3
"""
Build an example corpus: query, download, ingest, and convert XML to HTML.

Usage:
    ./venv/bin/python scripts/build_example_corpus.py \
        --config config/climate_change_2026.yaml
"""

import argparse
import json
from pathlib import Path

from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.corpus_review.query_run import (
    build_query_run_record,
    load_pilot_config,
    save_query_run_record,
    summarize_query_run,
)
from semantic_corpus.corpus_review.review_table import (
    build_review_rows_from_search_results,
    export_review_tables,
)
from semantic_corpus.corpus_review.workflow import run_repository_search
from semantic_corpus.ingestion.query_output_ingester import ingest_query_output_directory
from semantic_corpus.transformation.xml_to_html import convert_corpus_xml_to_html
from semantic_corpus.utils import get_project_temp_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build example corpus from query config.")
    parser.add_argument(
        "--config",
        type=str,
        default="config/climate_change_2026.yaml",
        help="YAML config with query, dates, limit, formats, corpus_name.",
    )
    parser.add_argument(
        "--corpus-dir",
        type=str,
        help="Corpus output directory (default: corpora/<corpus_name>).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_pilot_config(Path(args.config))

    query_name = config["query_name"]
    output_dir = Path(
        get_project_temp_dir(),
        "queries",
        config.get("output_subdir") or query_name,
    )
    corpus_dir = Path(args.corpus_dir) if args.corpus_dir else Path("corpora", config["corpus_name"])
    formats = config.get("formats") or ["xml", "pdf"]

    print(f"Query: {config['query_string']}")
    print(f"Dates: {config.get('start_date')} to {config.get('end_date')}")
    print(f"Limit: {config.get('limit', 50)} | Formats: {formats}")

    results, downloaded_count = run_repository_search(
        query_string=config["query_string"],
        repository=config.get("repository") or "europe_pmc",
        limit=int(config.get("limit") or 50),
        output_dir=output_dir,
        formats=formats,
        start_date=config.get("start_date"),
        end_date=config.get("end_date"),
    )

    results_path = Path(output_dir, "search_results.json")
    with open(results_path, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)

    record = build_query_run_record(
        query_name=query_name,
        query_string=config["query_string"],
        repository=config.get("repository") or "europe_pmc",
        limit=int(config.get("limit") or 50),
        formats=formats,
        output_dir=output_dir,
        result_count=len(results),
        downloaded_count=downloaded_count,
    )
    save_query_run_record(record, output_dir)
    print(summarize_query_run(record))

    rows = build_review_rows_from_search_results(
        results_path,
        xml_dir=output_dir,
        query_name=query_name,
        query_string=config["query_string"],
    )
    review_paths = export_review_tables(rows, Path(output_dir, "review"))
    print(f"Review table: {review_paths['markdown']}")

    corpus = CorpusManager(corpus_dir, use_bagit=True)
    corpus.create_structured_directories()
    added = ingest_query_output_directory(output_dir, corpus)
    print(f"Ingested {len(added)} papers into {corpus_dir}")

    html_paths = convert_corpus_xml_to_html(corpus_dir)
    print(f"Converted {len(html_paths)} XML files to HTML")
    if html_paths:
        sample = next(iter(html_paths.values()))
        print(f"Sample HTML: {sample}")

    if corpus.bagit_manager:
        corpus.bagit_manager.update_manifest()
    print("Done.")


if __name__ == "__main__":
    main()
