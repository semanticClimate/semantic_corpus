#!/usr/bin/env python3
"""Example: Step 0 — search repository, download, optional BAGIT.

Usage:
  ./venv/bin/python examples/cluster_review/step0_create_from_query.py \\
      --query '("marine heatwave") AND OPEN_ACCESS:Y AND HAS_FT:Y' \\
      --query-name step0_live_demo --limit 3 --create-bagit
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from semantic_corpus.cluster_review import create_corpus_from_query
from semantic_corpus.utils import get_project_temp_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cluster-review Step 0 example")
    parser.add_argument("--query", required=True, help="Repository query string")
    parser.add_argument("--query-name", default="step0_example", help="Run name")
    parser.add_argument(
        "--repository",
        default="europe_pmc",
        help="Repository key, or comma-separated list",
    )
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument(
        "--formats",
        default="xml",
        help="Comma-separated formats (default: xml)",
    )
    parser.add_argument(
        "--query-dir",
        type=str,
        help="Raw download dir (default: temp/queries/<query-name>)",
    )
    parser.add_argument(
        "--corpus-dir",
        type=str,
        help="BAGIT dir (default: corpora/<query-name>)",
    )
    parser.add_argument(
        "--create-bagit",
        action="store_true",
        help="Ingest downloads into a BAGIT corpus",
    )
    parser.add_argument(
        "--no-bagit",
        action="store_true",
        help="Skip BAGIT (raw query dir + review table only)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    create_bagit = bool(args.create_bagit) and not bool(args.no_bagit)
    repos = [r.strip() for r in args.repository.split(",") if r.strip()]
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    query_dir = (
        Path(args.query_dir)
        if args.query_dir
        else Path(get_project_temp_dir(), "queries", args.query_name)
    )
    corpus_dir = (
        Path(args.corpus_dir)
        if args.corpus_dir
        else Path("corpora", args.query_name)
    )

    print("Step 0: create_corpus_from_query")
    print(f"  query: {args.query}")
    print(f"  repos:  {repos}")
    print(f"  limit:  {args.limit}")
    print(f"  query_dir: {query_dir}")
    print(f"  create_bagit: {create_bagit}")

    summary = create_corpus_from_query(
        query_string=args.query,
        query_name=args.query_name,
        query_dir=query_dir,
        repositories=repos,
        limit=args.limit,
        formats=formats,
        corpus_dir=corpus_dir if create_bagit else None,
        create_bagit=create_bagit,
    )

    # Drop bulky rows from printed summary
    printable = {k: v for k, v in summary.items() if k != "rows"}
    print(json.dumps(printable, indent=2, ensure_ascii=False))
    print(summary.get("query_run_summary", ""))


if __name__ == "__main__":
    main()
