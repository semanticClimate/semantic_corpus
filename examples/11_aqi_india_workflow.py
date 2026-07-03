#!/usr/bin/env python3
"""
Example 11: AQI India corpus workflow (query, review table, chatbot export).

Run pilot search, ingest pygetpapers output, generate review tables, export for chatbot.
"""

from pathlib import Path

from semantic_corpus.corpus_review.workflow import (
    export_reviewed_corpus_for_chatbot,
    ingest_and_review_pygetpapers,
    run_pilot_from_config,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path(REPO_ROOT, "config", "aqi_india_pilot.yaml")
QUERY_DIR = Path(REPO_ROOT, "temp", "queries", "aqi_india_pilot")
CORPUS_DIR = Path(REPO_ROOT, "corpora", "aqi_india_pilot")
EXPORT_DIR = Path(REPO_ROOT, "temp", "exports", "aqi_india_chatbot")


def main() -> None:
    record = run_pilot_from_config(CONFIG)
    print(record["summary"])

    if not QUERY_DIR.is_dir():
        print(f"Query output not found: {QUERY_DIR}")
        return

    paths = ingest_and_review_pygetpapers(
        QUERY_DIR,
        CORPUS_DIR,
        query_run_path=Path(QUERY_DIR, "query_run.json"),
    )
    print(f"Review tables: {paths}")

    review_json = Path(CORPUS_DIR, "analysis", "review", "review_table.json")
    manifest = export_reviewed_corpus_for_chatbot(
        CORPUS_DIR,
        EXPORT_DIR,
        review_table_path=review_json,
    )
    print(f"Chatbot manifest: {manifest}")


if __name__ == "__main__":
    main()
