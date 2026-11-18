#!/usr/bin/env python3
"""Example: Step 3 — bipartite clusters from phrase cache.

Usage:
  ./venv/bin/python examples/cluster_review/step3_build_clusters.py \\
      --corpus-dir corpora/amoc_india_2026
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from semantic_corpus.cluster_review import build_clusters, list_demo_corpora


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cluster-review Step 3 example")
    parser.add_argument("--corpus-dir", type=str, help="Path to BAGIT corpus")
    parser.add_argument("--demo", type=str, help="Demo preset name")
    parser.add_argument("--list-demos", action="store_true")
    parser.add_argument(
        "--algorithm",
        choices=["louvain", "greedy"],
        default="louvain",
        help="Community detection algorithm (default: louvain)",
    )
    parser.add_argument(
        "--resolution",
        type=float,
        default=1.0,
        help="Louvain/greedy resolution (default: 1.0)",
    )
    parser.add_argument(
        "--min-cluster-papers",
        type=int,
        default=2,
        help="Min papers for a community to count as a cluster (default: 2)",
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

    print("Step 3: build_clusters")
    print(f"  corpus_dir: {corpus_dir}")
    summary = build_clusters(
        corpus_dir,
        algorithm=args.algorithm,
        resolution=args.resolution,
        min_cluster_papers=args.min_cluster_papers,
    )
    printable = {
        k: v
        for k, v in summary.items()
        if k not in ("clusters", "orphans")
    }
    print(json.dumps(printable, indent=2, ensure_ascii=False))
    print(
        f"Clusters: {summary['cluster_count']} · "
        f"orphan papers: {summary['orphan_paper_count']} · "
        f"edges: {summary['edge_count']}"
    )
    for cluster in (summary.get("clusters") or [])[:5]:
        print(
            f"  [{cluster['cluster_id']}] papers={cluster['paper_count']} "
            f"theme={cluster['theme'][:80]}"
        )


if __name__ == "__main__":
    main()
