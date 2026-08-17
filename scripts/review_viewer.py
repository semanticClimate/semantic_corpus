#!/usr/bin/env python3
"""Build and serve an HTML corpus review viewer.

Usage:
    ./venv/bin/python scripts/review_viewer.py build \
        --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
        --query-dir temp/queries/climate_anxiety_2026 \
        --min-score 1

    ./venv/bin/python scripts/review_viewer.py serve \
        --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
        --query-dir temp/queries/climate_anxiety_2026
"""

import argparse
import webbrowser
from pathlib import Path

from semantic_corpus.core.exceptions import CorpusError
from semantic_corpus.corpus_review.html_viewer import write_review_viewer
from semantic_corpus.corpus_review.interactive_review import ReviewSessionConfig
from semantic_corpus.corpus_review.review_viewer_server import ReviewViewerServer, infer_corpus_dir


def add_shared_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--review-table", required=True, help="Path to review_table.json")
    parser.add_argument("--query-dir", help="Query output directory")
    parser.add_argument("--xml-dir", help="Directory with downloaded XML files")
    parser.add_argument("--corpus-dir", help="Optional BAGIT corpus directory")
    parser.add_argument("--search-results", help="Optional search_results.json path")
    parser.add_argument("--min-score", type=int, help="Initial min score filter")
    parser.add_argument("--max-score", type=int, help="Initial max score filter")
    parser.add_argument(
        "--status",
        default="review",
        choices=["review", "include", "exclude", "all"],
        help="Initial status filter",
    )
    parser.add_argument("--topic", help="Initial topic filter")
    parser.add_argument("--redo", action="store_true", help="Include decided rows in queue")
    parser.add_argument("--intro-chars", type=int, default=800)


def build_config(args: argparse.Namespace) -> ReviewSessionConfig:
    review_table = Path(args.review_table)
    query_dir = Path(args.query_dir) if args.query_dir else review_table.parent.parent
    corpus_dir = Path(args.corpus_dir) if args.corpus_dir else infer_corpus_dir(query_dir)
    return ReviewSessionConfig(
        review_table_path=review_table,
        query_dir=query_dir if query_dir.exists() else None,
        xml_dir=Path(args.xml_dir) if args.xml_dir else None,
        corpus_dir=corpus_dir,
        search_results_path=Path(args.search_results) if args.search_results else None,
        min_score=args.min_score,
        max_score=args.max_score,
        status_filter=args.status,
        topic_filter=args.topic,
        redo=args.redo,
        intro_max_chars=args.intro_chars,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HTML corpus review viewer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Generate review_viewer.html")
    add_shared_args(build_parser)
    build_parser.add_argument(
        "--output",
        help="Output HTML path (default: alongside review_table.json)",
    )

    serve_parser = subparsers.add_parser("serve", help="Build viewer and start local server")
    add_shared_args(serve_parser)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument(
        "--html",
        help="Viewer HTML path (default: review/review_viewer.html)",
    )

    return parser.parse_args()


def default_html_path(review_table: Path) -> Path:
    return review_table.parent / "review_viewer.html"


def main() -> None:
    args = parse_args()
    config = build_config(args)
    review_table = Path(config.review_table_path)

    if args.command == "build":
        output = Path(args.output) if args.output else default_html_path(review_table)
        path = write_review_viewer(config, output)
        print(f"Wrote {path}")
        return

    html_path = Path(args.html) if args.html else default_html_path(review_table)
    write_review_viewer(config, html_path)

    review_dir = review_table.parent
    index_path = review_dir / "index.html"
    if not index_path.is_file():
        index_path.write_text(
            '<!DOCTYPE html><html><head>'
            '<meta http-equiv="refresh" content="0; url=review_table.html">'
            "</head><body><p><a href=\"review_table.html\">Open review table</a></p></body></html>",
            encoding="utf-8",
        )

    server = ReviewViewerServer(
        review_dir=review_dir,
        review_table_path=review_table,
        session_config=config,
        host=args.host,
        port=args.port,
    )
    table_url = f"http://{args.host}:{args.port}/review_table.html"
    print(f"  Open this URL: {table_url}")
    try:
        webbrowser.open(table_url)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()


if __name__ == "__main__":
    try:
        main()
    except CorpusError as exc:
        raise SystemExit(str(exc)) from exc
