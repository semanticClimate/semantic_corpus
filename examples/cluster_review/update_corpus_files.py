#!/usr/bin/env python3
"""Example: update an existing BAGIT with additional files (PDFs).

Usage:
  ./venv/bin/python examples/cluster_review/update_corpus_files.py \\
      --corpus-dir corpora/amoc_india_2026 --formats pdf
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from semantic_corpus.cluster_review import list_demo_corpora, update_bagit_formats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update BAGIT corpus with additional document formats (PDF)"
    )
    parser.add_argument("--corpus-dir", type=str, help="Path to BAGIT corpus")
    parser.add_argument("--demo", type=str, help="Demo preset name")
    parser.add_argument("--list-demos", action="store_true")
    parser.add_argument(
        "--formats",
        default="pdf",
        help="Comma-separated formats to fetch (default: pdf)",
    )
    parser.add_argument(
        "--repository",
        default="europe_pmc",
        help="Repository key (default: europe_pmc)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even when a valid PDF already exists",
    )
    parser.add_argument(
        "--paper-id",
        action="append",
        dest="paper_ids",
        help="Limit to one paper id (repeatable)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    demos = list_demo_corpora()
    if args.list_demos:
        print(json.dumps({k: str(v) for k, v in demos.items()}, indent=2))
        return 0

    if args.demo:
        if args.demo not in demos:
            print(
                f"Unknown demo '{args.demo}'. Available: {', '.join(sorted(demos))}",
                file=sys.stderr,
            )
            return 2
        corpus_dir = demos[args.demo]
    elif args.corpus_dir:
        corpus_dir = Path(args.corpus_dir)
    else:
        print("Provide --corpus-dir or --demo (or --list-demos)", file=sys.stderr)
        return 2

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    print(f"Update BAGIT files: corpus={corpus_dir} formats={formats}")

    def _progress(i: int, total: int, paper_id: str, status: str) -> None:
        print(f"  [{i}/{total}] {paper_id}: {status}")

    summary = update_bagit_formats(
        corpus_dir,
        formats=formats,
        repository=args.repository,
        force=args.force,
        paper_ids=args.paper_ids,
        progress_callback=_progress,
    )
    printable = {k: v for k, v in summary.items() if k != "papers"}
    print(json.dumps(printable, indent=2, ensure_ascii=False))
    print(
        f"Downloaded {summary['downloaded']} · skipped {summary['skipped']} · "
        f"failed {summary['failed']}"
    )
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
