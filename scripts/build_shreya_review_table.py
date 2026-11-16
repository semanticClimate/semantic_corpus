#!/usr/bin/env python3
"""
Build review table for Shreya's global warming and temperature rise query.

This script generates HTML, JSON, CSV, and Markdown review tables from the
search_results.json file in corpora/shreya_project/temp/queries/global_warming_temperature_rise/
"""

from pathlib import Path
from semantic_corpus.corpus_review.review_table import (
    build_review_rows_from_search_results,
    export_review_tables,
    load_query_context,
)


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    query_dir = Path(repo_root, "corpora", "shreya_project", "temp", "queries", "global_warming_temperature_rise")
    
    if not query_dir.is_dir():
        raise SystemExit(f"Query directory not found: {query_dir}")
    
    search_results_path = Path(query_dir, "search_results.json")
    query_run_path = Path(query_dir, "query_run.json")
    output_dir = Path(query_dir, "review")
    
    # Load query context from query_run.json
    context = load_query_context(query_run_path)
    
    # Build review rows from search results
    rows = build_review_rows_from_search_results(
        search_results_path,
        xml_dir=query_dir,
        query_name=context["query_name"],
        query_string=context["query_string"],
    )
    
    # Export review tables in all formats
    paths = export_review_tables(rows, output_dir, basename="review_table")
    
    # Print summary
    include_hint = sum(1 for r in rows if r["score"] >= 5)
    print(f"\n{'='*70}")
    print(f"Review Table Generation Complete")
    print(f"{'='*70}")
    print(f"Total Rows: {len(rows)}")
    print(f"High-score (>=5): {include_hint}")
    print(f"Query: {context['query_name'] or '(none)'}")
    print(f"\nGenerated files:")
    for fmt, path in sorted(paths.items()):
        print(f"  {fmt:12s}: {path}")
    print(f"\nOutput directory: {output_dir}")
    print(f"\nTo view the review table, run:")
    print(f"  ./venv/bin/python scripts/review_viewer.py serve \\")
    print(f"    --review-table {Path(output_dir, 'review_table.json')} \\")
    print(f"    --query-dir {query_dir}")
    print(f"\nThen open: http://127.0.0.1:8765/review_table.html")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
