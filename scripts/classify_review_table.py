#!/usr/bin/env python3
"""
Classify papers in an existing review table.

Adds unsupervised clusters and/or supervised encyclopedia categories to a
review_table.json, then re-exports review_table.{json,csv,md}.

Usage:
    # Unsupervised clustering only
    ./venv/bin/python scripts/classify_review_table.py \
        --review-json temp/queries/aqi_india_pilot/review/review_table.json \
        --clusters 5

    # Supervised using climate encyclopedias plus clustering
    ./venv/bin/python scripts/classify_review_table.py \
        --review-json temp/queries/aqi_india_pilot/review/review_table.json \
        --search-results temp/queries/aqi_india_pilot/search_results.json \
        --clusters 5 \
        --encyclopedia-dir ../encyclopedia
"""

import argparse
import json
from pathlib import Path

from semantic_corpus.classification.annotate import (
    annotate_rows_with_clusters,
    annotate_rows_with_encyclopedia,
    documents_from_review_rows,
    documents_from_search_results,
)
from semantic_corpus.classification.encyclopedia_labels import (
    load_encyclopedia_categories,
)
from semantic_corpus.corpus_review.review_table import export_review_tables


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify papers in a review table (clusters + encyclopedia)."
    )
    parser.add_argument(
        "--review-json",
        type=str,
        required=True,
        help="Path to review_table.json to annotate.",
    )
    parser.add_argument(
        "--search-results",
        type=str,
        help="Optional search_results.json for full-abstract text.",
    )
    parser.add_argument(
        "--clusters",
        type=int,
        default=5,
        help="Number of unsupervised clusters (0 to skip clustering).",
    )
    parser.add_argument(
        "--encyclopedia-dir",
        type=str,
        help="Path to ../encyclopedia for supervised classification.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Where to write review tables (default: review-json folder).",
    )
    parser.add_argument(
        "--basename",
        type=str,
        default="review_table",
        help="Basename for output files (default: review_table).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    review_json = Path(args.review_json)
    with open(review_json, "r", encoding="utf-8") as handle:
        rows = json.load(handle)

    if args.search_results and Path(args.search_results).is_file():
        documents = documents_from_search_results(Path(args.search_results))
    else:
        documents = documents_from_review_rows(rows)

    if args.clusters and args.clusters > 0:
        cluster_terms = annotate_rows_with_clusters(
            rows, documents=documents, n_clusters=args.clusters
        )
        print(f"Unsupervised: {len(cluster_terms)} clusters")
        for index, terms in sorted(cluster_terms.items()):
            print(f"  cluster {index}: {', '.join(terms)}")

    if args.encyclopedia_dir:
        categories = load_encyclopedia_categories(Path(args.encyclopedia_dir))
        results = annotate_rows_with_encyclopedia(
            rows, categories, documents=documents
        )
        classified = sum(1 for r in results.values() if r["category"])
        print(
            f"Supervised: {len(categories)} categories, "
            f"{classified}/{len(rows)} papers classified"
        )

    output_dir = Path(args.output_dir) if args.output_dir else review_json.parent
    paths = export_review_tables(rows, output_dir, basename=args.basename)
    print("Review tables:")
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")


if __name__ == "__main__":
    main()
