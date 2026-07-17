# Runbook: ocean heatwaves demo corpus

**Date:** 2026-07-16 (system date of generation)  
**Config:** [config/ocean_heatwaves_2026.yaml](../../config/ocean_heatwaves_2026.yaml)  
**Proposal:** [ocean_heatwaves_proposal.md](ocean_heatwaves_proposal.md)  
**Progress log (append-only):** [ocean_heatwaves_progress.md](ocean_heatwaves_progress.md)  
**Record:** [../records/2026-07-16_ocean_heatwaves_demo.md](../records/2026-07-16_ocean_heatwaves_demo.md)

This runbook walks through the semantic_corpus demo pipeline for **marine heatwaves and ocean currents**. Phases P0–P4 are defined in the proposal; this document covers all acts with exact commands.

### Acquisition note (2026-07-16)

P1 search/download used **`semantic_corpus` Europe PMC** (`build_example_corpus.py` / `run_repository_search`), **not** the pygetpapers CLI. Output is a flat query directory under `temp/queries/ocean_heatwaves_2026/`.

### Latest harvest snapshot (2026-07-16)

| Metric | Value |
|--------|-------|
| Rows | 50 (all `review` until manual filtering) |
| XML | 49 |
| PDF | 10 (publisher OA/Free; Europe PMC `?pdf=render` mostly 404) |

---

## Prerequisites

From the repository root:

```bash
cd /path/to/semantic_corpus
source venv/bin/activate   # or use ./venv/bin/python below
```

You need network access for Europe PMC search and download.

---

## Paths (reference)

| Artefact | Path |
|----------|------|
| Config | `config/ocean_heatwaves_2026.yaml` |
| Query output | `temp/queries/ocean_heatwaves_2026/` |
| Review table | `temp/queries/ocean_heatwaves_2026/review/review_table.json` |
| BAGIT corpus | `corpora/ocean_heatwaves_2026/` |
| Chatbot export | `temp/exports/ocean_heatwaves_2026/chatbot_manifest.json` |
| PRISMA outputs | `corpora/ocean_heatwaves_2026/data/analysis/prisma/` |

---

## Act 1–2 — Query, download, ingest, review table (P1)

**Recommended one-shot script** (search, download, review table, BAGIT ingest, XML→HTML):

```bash
./venv/bin/python scripts/build_example_corpus.py \
  --config config/ocean_heatwaves_2026.yaml
```

This writes:

- `temp/queries/ocean_heatwaves_2026/search_results.json`
- `temp/queries/ocean_heatwaves_2026/query_run.json`
- `PMC*.xml` and `PMC*.pdf` (when downloads succeed)
- `temp/queries/ocean_heatwaves_2026/review/review_table.{json,html,csv,md}`
- `corpora/ocean_heatwaves_2026/` (BAGIT corpus)

**Alternative — search + download only** (no ingest):

```python
from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_pilot_from_config

record = run_pilot_from_config(Path("config", "ocean_heatwaves_2026.yaml"))
print(record["summary"])
```

Note: `run_pilot_from_config` does not apply `start_date` / `end_date` from the YAML; use `build_example_corpus.py` when date filtering is required.

**Check download completeness** (printed automatically; also available via PRISMA build):

```bash
./venv/bin/python scripts/build_prisma_diagram.py \
  --corpus-dir corpora/ocean_heatwaves_2026 \
  --query-dir temp/queries/ocean_heatwaves_2026
```

If downloads are incomplete, the CLI exits with status 1 unless `--allow-incomplete-downloads` is passed.

---

## Act 3 — Refresh review table only

If you already have query output and need to rebuild the table:

```bash
./venv/bin/python scripts/build_review_table.py \
  --query-dir temp/queries/ocean_heatwaves_2026
```

**Source of truth:** `review_table.json`.

---

## Act 4 — Manual filtering (review viewer)

**Important:** Serve over HTTP — do not open the HTML file directly (`file://` breaks paper loading).

```bash
./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/ocean_heatwaves_2026/review/review_table.json \
  --query-dir temp/queries/ocean_heatwaves_2026
```

Open the printed URL, e.g. `http://127.0.0.1:8765/review_table.html`.

**Reviewer workflow:**

1. Click a row to read PDF or HTML in the viewer pane.
2. Set **include**, **exclude**, or leave as **review**.
3. Add **review notes** (e.g. “AMOC”, “MHW attribution”).
4. Click **Save review table** (writes back to JSON).

**Suggested demo targets:**

| Status | Approx. count |
|--------|---------------|
| `include` | 25–35 |
| `exclude` | 10–15 |
| `review` | remainder |

Tutorials: [html_review_table_tutorial.md](../tutorials/html_review_table_tutorial.md), [new_member_review_quickstart.md](../tutorials/new_member_review_quickstart.md).

---

## Act 5 — Sync review into corpus (after editing)

If review was done on the query-dir table before ingest, re-run ingest or copy the JSON:

```bash
./venv/bin/python scripts/build_example_corpus.py \
  --config config/ocean_heatwaves_2026.yaml
```

Or ingest manually after pygetpapers layout exists:

```python
from pathlib import Path
from semantic_corpus.corpus_review.workflow import ingest_and_review_pygetpapers

paths = ingest_and_review_pygetpapers(
    Path("temp", "queries", "ocean_heatwaves_2026"),
    Path("corpora", "ocean_heatwaves_2026"),
    query_run_path=Path("temp", "queries", "ocean_heatwaves_2026", "query_run.json"),
)
print(paths)
```

---

## Act 6 — PRISMA diagram (optional)

```bash
./venv/bin/python scripts/build_prisma_diagram.py \
  --corpus-dir corpora/ocean_heatwaves_2026 \
  --query-dir temp/queries/ocean_heatwaves_2026
```

Optional SVG (requires Graphviz `dot`):

```bash
dot -Tsvg corpora/ocean_heatwaves_2026/data/analysis/prisma/prisma_flow.dot \
  -o corpora/ocean_heatwaves_2026/data/analysis/prisma/prisma_flow.svg
```

See [prisma_flow.md](../prisma_flow.md).

---

## Act 7 — Chatbot export (P1)

After setting `review_status` to `include` for selected papers:

```python
from pathlib import Path
from semantic_corpus.corpus_review.workflow import export_reviewed_corpus_for_chatbot

manifest = export_reviewed_corpus_for_chatbot(
    Path("corpora", "ocean_heatwaves_2026"),
    Path("temp", "exports", "ocean_heatwaves_2026"),
    review_table_path=Path(
        "corpora", "ocean_heatwaves_2026", "analysis", "review", "review_table.json"
    ),
)
print(manifest)
```

Contract: [chatbot_export_contract.md](../chatbot_export_contract.md).

Only papers with `review_status == include` are exported by default.

---

## Act 8 — Encyclopedia (P2, planned)

Build curated terms from **included** papers using sibling repo `../encyclopedia`:

1. Extract keyword CSVs from corpus HTML/XML (adapt `encyclopedia/ipcc/phase1_wordlist.py`).
2. Curate wordlist (team adjudication).
3. Run `encyclopedia/utils/encyclopedia_builder.py` for Wikipedia-enriched entries.
4. Store under `corpora/ocean_heatwaves_2026/encyclopedia/` (proposed layout).

Glue script not yet in semantic_corpus — see [orat_plan.md](../orat_plan.md) Phase 2.

---

## Act 9 — ClimateInsight RAG + Cloudflare (P3 done; P4 next)

**Target repo:** [github.com/semanticClimate/ClimateInsight](https://github.com/semanticClimate/ClimateInsight)

**P3 (done):** manifest adapter — see `ClimateInsight/docs/manifest_adapter_outline.md`.

**P4 (rehearsal):**

1. Ingest a non-empty `chatbot_manifest.json` into ChromaDB:

```bash
source .venv/bin/activate
cd backend
python -m ingest.ingest --manifest /path/to/chatbot_manifest.json
```

2. Start backend and frontend per ClimateInsight README.
3. Share via Cloudflare Quick Tunnels:

```bash
cd /path/to/ClimateInsight
python3 scripts/inject-tunnel.py
```

**Sample demo questions:**

- How are marine heatwaves linked to changes in ocean circulation?
- What role does the AMOC play in regional heat extremes?
- How do Gulf Stream variations affect coastal heatwave intensity?

---

## Fallback corpus

If live harvest fails during a demo, use the known-good **climate_anxiety_2026** review table:

```bash
./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
  --query-dir temp/queries/climate_anxiety_2026
```

Explain that the **same pipeline** applies; only the query topic differs.

---

## Phase checklist

| Phase | Deliverable | Status |
|-------|-------------|--------|
| P0 | Config + this runbook + proposal | ✅ 2026-07-16 |
| P1 | Execute harvest, review, ingest, export | ✅ 2026-07-16 (PDFs partial: 10/50) |
| P2 | Encyclopedia glue + sample | Pending |
| P3 | ClimateInsight manifest ingest | ✅ 2026-07-16 |
| P4 | Rehearsal + Cloudflare dry run | **Next** |

Append session notes to [ocean_heatwaves_progress.md](ocean_heatwaves_progress.md).

---

## Verify P0 config loads

```bash
./venv/bin/python -c "
from pathlib import Path
from semantic_corpus.corpus_review.query_run import load_pilot_config
c = load_pilot_config(Path('config/ocean_heatwaves_2026.yaml'))
assert c['query_name'] == 'ocean_heatwaves_2026'
assert c['limit'] == 50
print('OK:', c['query_name'], c['limit'], c['repository'])
"
```
