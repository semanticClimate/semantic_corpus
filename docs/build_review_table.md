# Build a review table from query output

**Date:** 2026-07-03 (system date)

## Purpose

After running a pilot search/download, you have a flat query directory:

- `search_results.json` — list of paper metadata from Europe PMC
- `{pmcid}.xml` — fulltext XML files alongside the JSON (when downloaded)
- `query_run.json` — query provenance (optional but recommended)

This step builds a **scored review table** so you can browse candidates and decide which papers to include in the corpus.

## Quick start

From the repository root:

```bash
./venv/bin/python scripts/build_review_table.py \
    --query-dir temp/queries/aqi_india_pilot
```

Output is written to `temp/queries/aqi_india_pilot/review/`:

| File | Use |
|------|-----|
| `review_table.json` | Edit `review_status` programmatically or by hand |
| `review_table.csv` | Browse and edit in a spreadsheet |
| `review_table.md` | Quick read-only overview sorted by score |

## Script options

```bash
./venv/bin/python scripts/build_review_table.py --help
```

| Option | Default | Meaning |
|--------|---------|---------|
| `--query-dir` | — | Directory with `search_results.json` and `query_run.json` |
| `--search-results` | — | Path to `search_results.json` (alternative to `--query-dir`) |
| `--xml-dir` | same as search results | Directory containing `{pmcid}.xml` files |
| `--query-run` | `<query-dir>/query_run.json` | Provenance record for `query_name` / `query_string` columns |
| `--output-dir` | `<query-dir>/review` | Where to write output files |
| `--basename` | `review_table` | Basename for `.json`, `.csv`, `.md` |

Example with explicit paths:

```bash
./venv/bin/python scripts/build_review_table.py \
    --search-results temp/queries/aqi_india_pilot/search_results.json \
    --output-dir temp/queries/aqi_india_pilot/review
```

## What the table contains

Each row includes:

- **score** — relevance ranking from `relevance_scorer.py` (does not auto-include papers)
- **review_status** — starts as `review`; set to `include` or `exclude` after human review
- **title, abstract, pmcid, pmid, doi** — from search metadata
- **has_xml / has_pdf** — whether fulltext files were downloaded
- **location_terms, pollutant_terms, health_terms** — keyword matches used in scoring
- **query_name, query_string** — from `query_run.json` when present

Rows are sorted by descending score, then `paper_id`.

## After building the table

1. Open `review_table.csv` or `review_table.json`.
2. Set `review_status` to `include` for papers you want in the corpus, or `exclude` to drop them.
3. Continue with ingest and chatbot export — see [aqi_india_corpus_workflow.md](aqi_india_corpus_workflow.md).

Papers with `has_xml = false` have metadata only (no PMC fulltext was downloaded).

## Python API

The script calls library code you can reuse in notebooks or workflows:

```python
from pathlib import Path
from semantic_corpus.corpus_review.review_table import (
    build_review_rows_from_search_results,
    export_review_tables,
    load_query_context,
)

query_dir = Path("temp", "queries", "aqi_india_pilot")
context = load_query_context(Path(query_dir, "query_run.json"))
rows = build_review_rows_from_search_results(
    Path(query_dir, "search_results.json"),
    query_name=context["query_name"],
    query_string=context["query_string"],
)
paths = export_review_tables(rows, Path(query_dir, "review"))
```

## Related layouts

| Input layout | Tool |
|--------------|------|
| Flat `search_results.json` + `{pmcid}.xml` (this doc) | `scripts/build_review_table.py` |
| Pygetpapers folder per paper (`PMC*/eupmc_result.json`) | `build_review_rows_from_pygetpapers` via [aqi_india_corpus_workflow.md](aqi_india_corpus_workflow.md) |
| Already ingested BAGIT corpus | `build_review_rows_from_corpus` |

See also [chatbot_export_contract.md](chatbot_export_contract.md).
