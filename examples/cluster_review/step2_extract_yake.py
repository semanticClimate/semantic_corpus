#!/usr/bin/env python3
"""Example: Step 2 — phrase extraction (default: corpus TF-IDF) with disk cache.

Usage:
  ./venv/bin/python examples/cluster_review/step2_extract_yake.py \\
      --corpus-dir corpora/step0_live_demo

  ./venv/bin/python examples/cluster_review/step2_extract_yake.py \\
      --demo step0_live_demo --force --method yake
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from semantic_corpus.cluster_review import (
    DEFAULT_METHOD,
    DEFAULT_N,
    clear_all_caches,
    extract_phrases,
    list_demo_corpora,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cluster-review Step 2 example")
    parser.add_argument("--corpus-dir", type=str, help="Path to BAGIT corpus")
    parser.add_argument("--demo", type=str, help="Demo preset name")
    parser.add_argument("--list-demos", action="store_true")
    parser.add_argument(
        "--method",
        choices=["tfidf", "yake"],
        default=DEFAULT_METHOD,
        help=f"Extractor (default: {DEFAULT_METHOD})",
    )
    parser.add_argument("--n", type=int, default=DEFAULT_N, help="Max n-gram (default 3)")
    parser.add_argument("--top", type=int, default=15, help="Phrases per paper")
    parser.add_argument("--force", action="store_true", help="Ignore cache and re-extract")
    parser.add_argument("--no-cache", action="store_true", help="Do not read cache")
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Delete all phrase caches for this corpus, then exit (unless combined with extract)",
    )
    parser.add_argument(
        "--clear-and-extract",
        action="store_true",
        help="Clear phrase caches, then run a fresh extract",
    )
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

    if args.clear_cache or args.clear_and_extract:
        cleared = clear_all_caches(corpus_dir)
        print(json.dumps(cleared, indent=2, ensure_ascii=False))
        if args.clear_cache and not args.clear_and_extract:
            return

    print("Step 2: extract_phrases")
    print(f"  corpus_dir: {corpus_dir}")
    print(f"  method={args.method} n={args.n} top={args.top} force={args.force}")

    def _progress(i: int, total: int, paper_id: str, elapsed: float) -> None:
        print(f"  [{i}/{total}] {paper_id} ({elapsed:.3f}s)")

    summary = extract_phrases(
        corpus_dir,
        method=args.method,
        n=args.n,
        top=args.top,
        use_cache=not args.no_cache,
        force=args.force,
        progress_callback=_progress,
    )
    printable = {
        k: v
        for k, v in summary.items()
        if k not in ("papers", "paper_ids")
    }
    print(json.dumps(printable, indent=2, ensure_ascii=False))
    print(
        f"Phrases: {summary['total_phrase_mentions']} mentions, "
        f"{summary['unique_phrases']} unique across {summary['paper_count']} papers"
    )
    for paper in summary.get("papers", [])[:3]:
        top = ", ".join(p["phrase"] for p in (paper.get("phrases") or [])[:5])
        print(f"  - {paper['paper_id']} [{paper['source']}]: {top}")


if __name__ == "__main__":
    main()
