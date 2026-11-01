#!/usr/bin/env python3
"""Example: Step 1 — load an existing BAGIT corpus.

Usage:
  ./venv/bin/python examples/cluster_review/step1_load_bagit.py \\
      --corpus-dir corpora/step0_live_demo

  ./venv/bin/python examples/cluster_review/step1_load_bagit.py --demo step0_live_demo
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from semantic_corpus.cluster_review import list_demo_corpora, load_bagit_corpus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cluster-review Step 1 example")
    parser.add_argument("--corpus-dir", type=str, help="Path to BAGIT corpus")
    parser.add_argument(
        "--demo",
        type=str,
        help="Demo preset name (see list_demo_corpora)",
    )
    parser.add_argument("--list-demos", action="store_true")
    parser.add_argument("--query-name", default="")
    parser.add_argument("--query-string", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    demos = list_demo_corpora()
    if args.list_demos:
        print(json.dumps({k: str(v) for k, v in demos.items()}, indent=2))
        return

    if args.demo:
        if args.demo not in demos:
            raise SystemExit(
                f"Unknown demo '{args.demo}'. Available: {', '.join(sorted(demos))}"
            )
        corpus_dir = demos[args.demo]
    elif args.corpus_dir:
        corpus_dir = Path(args.corpus_dir)
    else:
        raise SystemExit("Provide --corpus-dir or --demo (or --list-demos)")

    print("Step 1: load_bagit_corpus")
    print(f"  corpus_dir: {corpus_dir}")
    summary = load_bagit_corpus(
        corpus_dir,
        query_name=args.query_name,
        query_string=args.query_string,
    )
    printable = {
        k: v
        for k, v in summary.items()
        if k not in ("rows", "papers")
    }
    print(json.dumps(printable, indent=2, ensure_ascii=False))
    print(f"Papers: {summary['paper_count']}")
    for paper in summary.get("papers", [])[:5]:
        print(f"  - {paper['paper_id']}: {paper['title'][:80]}")


if __name__ == "__main__":
    main()
