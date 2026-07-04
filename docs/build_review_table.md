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
| `review_table.json` | Source of truth for tools |
| `review_table.csv` | Machine export (spreadsheet interchange; not for editing) |
| `review_table.html` | **Human editing** in any browser; styled via `review_table.css` |
| `review_table.css` | Edit layout/colours (platform-independent) |
| `review_table.md` | Quick read-only overview |

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

## Edit in HTML (recommended)

**Team tutorial:** [tutorials/html_review_table_tutorial.md](tutorials/html_review_table_tutorial.md)  
**Feature record:** [records/2026-07-04_html_review_table.md](records/2026-07-04_html_review_table.md)

Papers load only through the local server (http:// URL). Do not open `review_table.html` as a saved file.

```bash
./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
  --query-dir temp/queries/climate_anxiety_2026
```

Then open **http://127.0.0.1:8765/review_table.html** (the script may open this for you).

- **Green banner** at top = connected; **Read** opens PDF/HTML in a side panel
- Change **Status** (`review` / `include` / `exclude`) and **Notes** in the table
- Click **Save review table** — updates `.json`, `.csv`, `.html`, and `.md`
- Customise appearance by editing `review_table.css` in the same folder (reload the page)

CSV is still exported for pipelines, but you do not need Excel to edit.

## After building the table (JSON / programmatic)

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

## Colab notebook

For a browser-based workflow (no local install), see [colab_corpus_review_notebook.md](colab_corpus_review_notebook.md) and [`notebooks/corpus_query_review_colab.ipynb`](../notebooks/corpus_query_review_colab.ipynb).
