# Interactive paper selection (Y/N review)

**Date:** 2026-07-04 (system date)

## Purpose

After building a review table, use this tool to manually decide which papers to
**include** or **exclude** in the corpus. It supports decisions based on:

- relevance **scores**
- matched **topics** (location / pollutant / health terms, plus optional cluster or encyclopedia columns when present)
- human reading of **title**, **abstract**, and an **introduction excerpt** from XML when available

## Quick start

```bash
./venv/bin/python scripts/interactive_review.py \
  --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
  --query-dir temp/queries/climate_anxiety_2026
```

The tool saves after every decision to:

- `review_table.json`
- `review_table.csv`
- `review_table.md`

## Keyboard commands

| Key | Action |
|-----|--------|
| `Y` | Mark **include** |
| `N` | Mark **exclude** |
| `S` | **Skip** (leave as `review`) |
| `U` | **Undo** last decision |
| `Q` | **Quit** and save |

You can add an optional note after each Y/N decision.

## Filtering before review

Review high-score health papers first:

```bash
./venv/bin/python scripts/interactive_review.py \
  --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
  --query-dir temp/queries/climate_anxiety_2026 \
  --min-score 1 \
  --topic health
```

Other useful flags:

| Flag | Meaning |
|------|---------|
| `--max-score` | Only show rows with score <= value |
| `--status review` | Default: only undecided rows |
| `--status all` | Revisit every row |
| `--redo` | Include rows already marked include/exclude |
| `--corpus-dir corpora/climate_anxiety_2026` | Look up fulltext in BAGIT corpus |
| `--intro-chars 1200` | Longer introduction excerpt |

## What you see for each paper

- score, current review status, identifiers
- topic matches and optional cluster / encyclopedia labels
- title, authors, journal, date
- full abstract (from `search_results.json` when available)
- introduction excerpt from `{pmcid}.xml` when downloaded

## Python API

```python
from pathlib import Path
from semantic_corpus.corpus_review.interactive_review import (
    ReviewSessionConfig,
    run_interactive_review,
)

config = ReviewSessionConfig(
    review_table_path=Path("temp/queries/climate_anxiety_2026/review/review_table.json"),
    query_dir=Path("temp/queries/climate_anxiety_2026"),
    min_score=1,
    topic_filter="health",
)
run_interactive_review(config)
```

## After selection

Export only included papers using the existing chatbot export workflow, or
filter `review_table.json` where `review_status == "include"`.

## Reporting interface problems

Describe what you saw and what you expected. Useful details:

1. **Steps** — command you ran or file you opened
2. **Screen text** — e.g. "Paper 1 of 0 in queue"
3. **What you clicked** — Include, Exclude, filters set
4. **Screenshot** — optional but helpful

Paste that in chat; no special format required.

## HTML review (recommended for teams)

- **New member (5 min):** [tutorials/new_member_review_quickstart.md](tutorials/new_member_review_quickstart.md)
- **Full tutorial:** [tutorials/html_review_table_tutorial.md](tutorials/html_review_table_tutorial.md)
- **Build table first:** [build_review_table.md](build_review_table.md)

Quick serve command (after building the table):

```bash
./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
  --query-dir temp/queries/climate_anxiety_2026
```

Open **http://127.0.0.1:8765/review_table.html** — not a `file://` path.

## HTML viewer (one paper at a time)

For a sidebar queue with Include / Exclude buttons, open **http://127.0.0.1:8765/review_viewer.html** (same server as above).

Build a standalone file without serving:

```bash
./venv/bin/python scripts/review_viewer.py build \
  --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
  --query-dir temp/queries/climate_anxiety_2026
```

See [records/2026-07-04_html_review_table.md](records/2026-07-04_html_review_table.md) for architecture notes.

See also [build_review_table.md](build_review_table.md).
