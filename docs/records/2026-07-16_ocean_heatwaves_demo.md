# Record: ocean_heatwaves_2026 end-to-end demo

**Date:** 2026-07-16 (system date of generation)  
**Status:** P0–P1 + P3 done; PDF partial; P2 pending; **P4 next**  
**Config:** [config/ocean_heatwaves_2026.yaml](../../config/ocean_heatwaves_2026.yaml)

**Related:**

- [Progress log (incremental)](../demo/ocean_heatwaves_progress.md)
- [Proposal](../demo/ocean_heatwaves_proposal.md)
- [Runbook](../demo/ocean_heatwaves_demo.md)
- [Summary](../summary/2026-07-16_ocean_heatwaves_demo.md)

---

## Goal

Demonstrate semantic_corpus range:

1. Issue query (ocean currents + marine heatwaves)
2. Download ~50 papers
3. Manually filter in HTML review table
4. Build encyclopedia (planned)
5. Export for ClimateInsight RAG (planned ingest)
6. Cloudflare chatbot share (planned)

---

## Acquisition stack (what we actually used)

| Layer | Choice |
|-------|--------|
| Search API | Europe PMC REST |
| Client | **`semantic_corpus.repositories.europe_pmc.EuropePMCRepository`** |
| Orchestration | `run_repository_search` / `scripts/build_example_corpus.py` |
| **Not used** | **pygetpapers** CLI or package |

Output is the **flat query directory** layout under `temp/queries/ocean_heatwaves_2026/`.

---

## Artefacts (as of 2026-07-16)

| Path | Notes |
|------|-------|
| `config/ocean_heatwaves_2026.yaml` | Query + limit + formats + dates |
| `temp/queries/ocean_heatwaves_2026/query_run.json` | Provenance |
| `temp/queries/ocean_heatwaves_2026/search_results.json` | 50 results |
| `temp/queries/ocean_heatwaves_2026/*.xml` | 49 files |
| `temp/queries/ocean_heatwaves_2026/*.pdf` | 10 files |
| `temp/queries/ocean_heatwaves_2026/review/` | Editable HTML + JSON source of truth |
| `corpora/ocean_heatwaves_2026/` | BAGIT (nested `data/data/` — see issues) |
| `temp/exports/ocean_heatwaves_2026/chatbot_manifest.json` | 0 papers until `include` |

---

## Counts (latest review table)

| Field | Value |
|-------|-------|
| Rows | 50 |
| `review_status` | all `review` |
| `has_xml` | 49 |
| `has_pdf` | 10 |

---

## Code changes this day

| File | Change |
|------|--------|
| `semantic_corpus/corpus_review/constants.py` | Resolved merge conflict; kept PRISMA/download constants |
| `semantic_corpus/repositories/europe_pmc.py` | Fetch metadata for PDF; multi-URL candidate download (OA + Free) |

---

## PDF download findings

1. Europe PMC `?pdf=render` → **404** for most papers on 2026-07-16 (system date).
2. NCBI `/pmc/articles/…/pdf/` → reCAPTCHA HTML.
3. Publisher PDF URLs in `fullTextUrlList` with availability **OA** or **F** → succeed when reachable.
4. Older on-disk PDFs (e.g. `climate_anxiety_2026`) still present; re-fetching those PMC IDs via render also fails now.

---

## Open engineering issues

1. BAGIT payload nested under `data/data/`; `list_papers()` / chatbot export expect `data/metadata` and `data/documents`.
2. Avoid double-ingest with `ingest_and_review_pygetpapers` after `build_example_corpus`.
3. Chatbot export empty until (a) review statuses set to `include` and (b) corpus path alignment fixed.

---

## Review viewer command

```bash
./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/ocean_heatwaves_2026/review/review_table.json \
  --query-dir temp/queries/ocean_heatwaves_2026
```
