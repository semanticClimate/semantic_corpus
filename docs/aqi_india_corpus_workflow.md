# AQI India corpus workflow

**Date:** 2026-07-03 (system date)

## Pilot configuration

See [config/aqi_india_pilot.yaml](../config/aqi_india_pilot.yaml):

- **Query:** `("air quality index" OR AQI OR "ambient air pollution" OR PM2.5 OR PM10) AND India`
- **Repository:** `europe_pmc`
- **Limit:** 25
- **Formats:** XML first
- **Corpus name:** `aqi_india_pilot`

## Workflow stages

1. **Issue query** — run search/download; record in `temp/queries/aqi_india_pilot/query_run.json`.
2. **Immediate reaction** — inspect `search_results.json` and review table; revise query if needed.
3. **Ingest** — pygetpapers-style output → BAGIT corpus via `ingest_pygetpapers_directory`.
4. **Review table** — scored rows in `review/review_table.{json,csv,md}` (flat query dir) or `analysis/review/` (after corpus ingest). See [build_review_table.md](build_review_table.md).
5. **Select** — set `review_status` to `include`, `review`, or `exclude` in JSON/CSV.
6. **Chatbot export** — `chatbot_manifest.json` for `../chatbot` (included papers only).

## Build review table (CLI)

After search/download to `temp/queries/aqi_india_pilot/`:

```bash
./venv/bin/python scripts/build_review_table.py \
    --query-dir temp/queries/aqi_india_pilot
```

See [build_review_table.md](build_review_table.md) for options and next steps.

## Colab notebook

Community users can run the same query → download → review flow in Google Colab: [colab_corpus_review_notebook.md](colab_corpus_review_notebook.md).

## Python usage

```python
from pathlib import Path
from semantic_corpus.corpus_review.workflow import (
    run_pilot_from_config,
    ingest_and_review_pygetpapers,
    export_reviewed_corpus_for_chatbot,
)

# 1. Run pilot search (live API)
record = run_pilot_from_config(Path("config", "aqi_india_pilot.yaml"))
print(record["summary"])

# 2. After pygetpapers download to same layout, ingest + review tables
paths = ingest_and_review_pygetpapers(
    Path("temp", "queries", "aqi_india_pilot"),
    Path("corpora", "aqi_india_pilot"),
    query_run_path=Path("temp", "queries", "aqi_india_pilot", "query_run.json"),
)

# 3. Export for chatbot (after editing review_status in review_table.json)
export_reviewed_corpus_for_chatbot(
    Path("corpora", "aqi_india_pilot"),
    Path("temp", "exports", "aqi_india_chatbot"),
    review_table_path=Path("corpora", "aqi_india_pilot", "analysis", "review", "review_table.json"),
)
```

## Review status semantics

| Status | Meaning |
|--------|---------|
| `include` | Selected for corpus and chatbot export |
| `review` | Default; needs human decision |
| `exclude` | Omit from chatbot export |

## Scoring

Relevance score ranks rows for review; it does **not** auto-include papers. See `semantic_corpus/corpus_review/relevance_scorer.py`.

See also [chatbot_export_contract.md](chatbot_export_contract.md).
