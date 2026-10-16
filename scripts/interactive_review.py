#!/usr/bin/env python3
"""Interactive Y/N review tool for corpus paper selection.

Usage:
    ./venv/bin/python scripts/interactive_review.py \
        --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
        --query-dir temp/queries/climate_anxiety_2026

Filter by score or topic before reviewing:
    ./venv/bin/python scripts/interactive_review.py \
        --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
        --query-dir temp/queries/climate_anxiety_2026 \
        --min-score 1 \
        --topic health
"""

import argparse
from pathlib import Path

from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.interactive_review import (
    ReviewSessionConfig,
    run_interactive_review,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive Y/N paper selection for corpus review tables."
    )
    parser.add_argument(
        "--review-table",
        required=True,
        help="Path to review_table.json",
    )
    parser.add_argument(
        "--query-dir",
        help="Query output directory with search_results.json and downloaded files",
    )
    parser.add_argument(
        "--xml-dir",
        help="Directory with {pmcid}.xml files (default: query-dir)",
    )
    parser.add_argument(
        "--corpus-dir",
        help="Optional ingested BAGIT corpus directory for fulltext lookup",
    )
    parser.add_argument(
        "--search-results",
        help="Optional path to search_results.json for full abstracts",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        help="Only review rows with score >= this value",
    )
    parser.add_argument(
        "--max-score",
        type=int,
        help="Only review rows with score <= this value",
    )
    parser.add_argument(
        "--status",
        default="review",
        choices=["review", "include", "exclude", "all"],
        help="Only review rows with this status (default: review)",
    )
    parser.add_argument(
        "--topic",
        help="Only review rows whose topic/title/abstract matches this term",
    )
    parser.add_argument(
        "--redo",
        action="store_true",
        help="Include rows already marked include/exclude",
    )
    parser.add_argument(
        "--intro-chars",
        type=int,
        default=800,
        help="Maximum characters for introduction excerpt (default: 800)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    review_table = Path(args.review_table)
    query_dir = Path(args.query_dir) if args.query_dir else review_table.parent.parent

    config = ReviewSessionConfig(
        review_table_path=review_table,
        query_dir=query_dir if query_dir.exists() else None,
        xml_dir=Path(args.xml_dir) if args.xml_dir else None,
        corpus_dir=Path(args.corpus_dir) if args.corpus_dir else None,
        search_results_path=Path(args.search_results) if args.search_results else None,
        min_score=args.min_score,
        max_score=args.max_score,
        status_filter=args.status,
        topic_filter=args.topic,
        redo=args.redo,
        intro_max_chars=args.intro_chars,
    )

    try:
        run_interactive_review(config)
    except CorpusError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
