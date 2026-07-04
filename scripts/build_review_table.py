#!/usr/bin/env python3
"""
Build a corpus review table from a semantic_corpus query output directory.

Reads a flat query output (search_results.json plus sibling {pmcid}.xml files,
as produced by the download workflow) and writes review_table.{json,csv,md,html}.

Usage:
    ./venv/bin/python scripts/build_review_table.py \
        --query-dir temp/queries/aqi_india_pilot

    # or point directly at files/dirs
    ./venv/bin/python scripts/build_review_table.py \
        --search-results temp/queries/aqi_india_pilot/search_results.json \
        --output-dir temp/queries/aqi_india_pilot/review
"""

import argparse
from pathlib import Path

from semantic_corpus.corpus_review.review_table import (
    build_review_rows_from_search_results,
    export_review_tables,
    load_query_context,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build review table from a query output directory."
    )
    parser.add_argument(
        "--query-dir",
        type=str,
        help="Query output dir containing search_results.json and query_run.json.",
    )
    parser.add_argument(
        "--search-results",
        type=str,
        help="Path to search_results.json (overrides --query-dir).",
    )
    parser.add_argument(
        "--xml-dir",
        type=str,
        help="Directory with {pmcid}.xml files (default: search_results folder).",
    )
    parser.add_argument(
        "--query-run",
        type=str,
        help="Path to query_run.json for provenance (default: alongside results).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Where to write review tables (default: <query-dir>/review).",
    )
    parser.add_argument(
        "--basename",
        type=str,
        default="review_table",
        help="Basename for output files (default: review_table).",
    )
    return parser.parse_args()


def resolve_paths(args: argparse.Namespace):
    if args.search_results:
        search_results = Path(args.search_results)
        query_dir = search_results.parent
    elif args.query_dir:
        query_dir = Path(args.query_dir)
        search_results = Path(query_dir, "search_results.json")
    else:
        raise SystemExit("Provide --query-dir or --search-results")

    xml_dir = Path(args.xml_dir) if args.xml_dir else search_results.parent
    query_run = (
        Path(args.query_run)
        if args.query_run
        else Path(query_dir, "query_run.json")
    )
    output_dir = Path(args.output_dir) if args.output_dir else Path(query_dir, "review")
    return search_results, xml_dir, query_run, output_dir


def main() -> None:
    args = parse_args()
    search_results, xml_dir, query_run, output_dir = resolve_paths(args)

    context = load_query_context(query_run)
    rows = build_review_rows_from_search_results(
        search_results,
        xml_dir=xml_dir,
        query_name=context["query_name"],
        query_string=context["query_string"],
    )
    paths = export_review_tables(rows, output_dir, basename=args.basename)

    include_hint = sum(1 for r in rows if r["score"] >= 5)
    print(f"Rows: {len(rows)} (high-score >=5: {include_hint})")
    print(f"Query: {context['query_name'] or '(none)'}")
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")


if __name__ == "__main__":
    main()
