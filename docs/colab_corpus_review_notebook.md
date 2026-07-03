# Colab notebook: query, download, and review

**Date:** 2026-07-03 (system date)

## Overview

The community notebook [`notebooks/corpus_query_review_colab.ipynb`](../notebooks/corpus_query_review_colab.ipynb) runs in Google Colab and lets you:

1. Install `semantic_corpus` from GitHub
2. Search Europe PMC and download XML fulltext
3. Build a scored review table
4. Browse and filter candidates
5. Download artifacts for offline review
6. Refine the query and compare runs

No local repository checkout is required.

## Open in Colab

After the notebook is on the default branch, use:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/semanticClimate/semantic_corpus/blob/main/notebooks/corpus_query_review_colab.ipynb)

Or upload `notebooks/corpus_query_review_colab.ipynb` manually to Colab.

## Parameters

Edit the parameters cell before each run:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `QUERY_NAME` | `aqi_india_pilot` | Short name for this run; used in output paths |
| `QUERY_STRING` | AQI India pilot query | Europe PMC search string |
| `LIMIT` | `25` | Maximum papers to retrieve |
| `FORMATS` | `["xml"]` | Download formats |
| `REPOSITORY` | `europe_pmc` | Repository key |
| `REVISION_OF` | `None` | Prior `QUERY_NAME` when refining a query |
| `OUTPUT_DIR` | `/content/queries/<QUERY_NAME>` | Where results are written |

## What gets written

Under `OUTPUT_DIR`:

| File / folder | Contents |
|---------------|----------|
| `search_results.json` | Metadata for all search hits |
| `{pmcid}.xml` | Fulltext XML when PMC fulltext is available |
| `query_run.json` | Provenance (query, counts, timestamp, `revision_of`) |
| `review/review_table.json` | Scored review rows |
| `review/review_table.csv` | Same data for spreadsheet editing |
| `review/review_table.md` | Quick read-only summary |

## Iterative refinement

After each run:

1. Check row counts and how many papers have XML (`has_xml`).
2. Scan high-score rows (score >= 5) in the pandas display.
3. Decide whether the query is too broad or too narrow.
4. Edit `QUERY_STRING` and set a new `QUERY_NAME`.
5. Set `REVISION_OF` to the previous query name.
6. Re-run sections 3–5 and use the compare cell to see overlap.

Example refined query:

```text
("air quality index" OR AQI OR PM2.5) AND India AND Delhi
```

## Review workflow

The notebook builds the table; human review happens offline:

1. Download `review_table.csv`.
2. Set `review_status` to `include` or `exclude` for each row.
3. Continue locally with BAGIT ingest and chatbot export.

See [build_review_table.md](build_review_table.md) and [aqi_india_corpus_workflow.md](aqi_india_corpus_workflow.md).

## Library API used by the notebook

The notebook calls `run_query_and_build_review_table(...)` in [`semantic_corpus/corpus_review/workflow.py`](../semantic_corpus/corpus_review/workflow.py), which:

- Runs `run_repository_search(...)` against Europe PMC
- Writes `search_results.json` and `query_run.json`
- Builds rows with `build_review_rows_from_search_results(...)`
- Exports `review/review_table.{json,csv,md}`

Display uses `review_rows_to_dataframe(...)` (requires pandas, installed in the notebook only).

## Known limitations

- **Colab sessions expire** — use Google Drive (section 7) to persist output.
- **No API key required** — Europe PMC REST is public; large `LIMIT` values take longer.
- **Metadata-only papers** — records without PMCID cannot download XML (`has_xml = false`).
- **v1 scope** — no in-notebook BAGIT ingest, `review_status` editing, or chatbot export.

## Related docs

- [build_review_table.md](build_review_table.md) — CLI and Python API for review tables
- [aqi_india_corpus_workflow.md](aqi_india_corpus_workflow.md) — full corpus workflow
- [chatbot_export_contract.md](chatbot_export_contract.md) — export format for RAG chatbots
