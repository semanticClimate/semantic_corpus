# Progress log: ocean_heatwaves_2026 demo

**Corpus:** `ocean_heatwaves_2026`  
**Purpose:** Append-only record of work. Newest entries at the **bottom**.  
**Started:** 2026-07-16 (system date)

---

## 2026-07-16 — Session start; style guides

- Read `../pygetpapers/docs/styleguide.md` and `../amilib/docs/style_guide_compliance.md`.
- System date verified: **2026-07-16**.
- Prior recommendation (from earlier session): best interactive review demo corpus was `climate_anxiety_2026`; new demo topic chosen separately (ocean heatwaves).

---

## 2026-07-16 — Proposal (no code)

- User requested demo covering: query → download 50 → review table → encyclopedia → ClimateInsight RAG → Cloudflare chatbot.
- Topic: **ocean currents and heatwaves**.
- Proposal drafted in chat; then saved to docs (next entry).

---

## 2026-07-16 — P0: docs + config

**User:** save plan to `docs/`, then run P0.

| Deliverable | Path |
|-------------|------|
| Proposal | `docs/demo/ocean_heatwaves_proposal.md` |
| Runbook | `docs/demo/ocean_heatwaves_demo.md` |
| Config | `config/ocean_heatwaves_2026.yaml` |

**Query (Europe PMC):**

```text
("marine heatwave" OR "ocean heat wave" OR "ocean heatwave")
AND ("ocean current" OR "ocean circulation" OR "Gulf Stream" OR "AMOC")
AND (HAS_FT:Y)
```

**Params:** limit 50; formats xml+pdf; dates 2020-01-01 … 2026-12-31; repository `europe_pmc`.

**Validation:** `load_pilot_config` loads successfully.

---

## 2026-07-16 — P1: harvest + ingest + PRISMA + export

**User:** run P1.

### Blocker fixed before harvest

- Merge conflict markers in `semantic_corpus/corpus_review/constants.py` caused `SyntaxError`.
- Resolved by keeping PRISMA / download-status constants (stashed side).

### Acquisition tool (important)

- Search/download used **semantic_corpus Europe PMC adapter**, **not** pygetpapers CLI/package.
- Entry points: `scripts/build_example_corpus.py` → `run_repository_search` → `EuropePMCRepository`.
- Output layout: flat query dir (`PMC*.xml`, `search_results.json`), not classic pygetpapers `PMC…/eupmc_result.json` folders.

### First harvest results

| Metric | Value |
|--------|-------|
| Retrieved | 50 |
| XML on disk | 49 |
| PDF on disk | **0** (first run) |
| Review rows | 50 (all `review`) |
| HTML converted | 49 |
| Ingested into BAGIT | 50 (reported) |

- Download completeness: **INCOMPLETE** (expected 100 files; found 49).
- PRISMA written under corpus (path nested — see known issues).
- Chatbot export: `temp/exports/ocean_heatwaves_2026/chatbot_manifest.json` with **0 papers** (no `include` yet — expected).

### Known issues noted during P1

1. **BAGIT nesting:** files land under `corpora/ocean_heatwaves_2026/data/data/…` (same pattern as other corpora). `CorpusManager.list_papers()` looks at `data/metadata/` → returns 0 → chatbot export empty even after includes unless paths aligned.
2. **Do not** run `ingest_and_review_pygetpapers` on top of `build_example_corpus` — nests the bag further and can wipe review tables.
3. PDF download for PMC IDs skipped metadata fetch → always used broken `?pdf=render` fallback (fixed later same day).

---

## 2026-07-16 — PDF re-download + review table refresh

**User:** rerun query to download PDFs; include in same table; slight paper-list discrepancies OK.

### Root cause

- For PMC IDs, `download_paper` did not call `_search_one_paper`, so `_find_pdf_url` got an empty record and fell back to `https://europepmc.org/articles/{pmcid}?pdf=render`.
- That endpoint currently returns **404** JSON for most OA papers (also verified for older `climate_anxiety_2026` PMCIDs that already have PDFs on disk from earlier successful downloads).
- NCBI PMC PDF URLs hit **reCAPTCHA**.
- Publisher OA/Free PDF URLs (Nature, Springer, etc.) still work when present in `fullTextUrlList`.

### Code changes (`semantic_corpus/repositories/europe_pmc.py`)

1. Fetch paper metadata when `"pdf"` is in formats and metadata is missing.
2. Collect ordered PDF URL candidates: publisher OA/`F` first, then NCBI, then Europe PMC render.
3. Try candidates until PDF bytes are obtained (`_download_pdf_bytes`).

### Re-run results (same query dir + rebuilt review table)

| Metric | Value |
|--------|-------|
| Rows | 50 |
| has_xml | 49 |
| has_pdf | **10** |
| XML files | 49 |
| PDF files | 10 |

**Papers with PDF (titles abbreviated):**

- PMC10468509 — Bay of Bengal MHWs 1982–2021
- PMC10011364 — Bottom MHWs North America shelves
- PMC10682185 — Ocean fronts as decadal thermostats
- PMC10808424 — MHW shifts pelagic microbiology
- PMC11733174 — North Pacific heat storage pattern
- PMC7653907 — Drivers/impacts extreme MHWs
- PMC7814029 — Complex networks of MHWs
- PMC9135278 — Pacific bluefin tuna (historical)
- PMC9381716 — Compound MHWs and ocean acidity extremes
- PMC8068737 — Coral reef bleaching tipping point

`query_run.json` notes updated to record PDF re-download and Europe PMC render failure.

---

## 2026-07-16 — Clarification: pygetpapers?

**User:** Did you use pygetpapers for the search?

**Answer recorded:** **No.** Used semantic_corpus’s own Europe PMC repository only.

---

## 2026-07-16 — Documentation pass

**User:** record incrementally everything to `docs/`.

- Added this progress log, demo README, dated record, and session summary.
- Updated runbook/proposal cross-links and P1 outcome notes.

---

## Next (not done)

| Phase | Status |
|-------|--------|
| Manual review (`include` / `exclude`) | Pending |
| Re-export chatbot manifest after includes | Pending |
| P2 encyclopedia | Pending |
| P3 ClimateInsight ingest | ✅ Done 2026-07-16 (adapter + 14 tests) |
| P4 Cloudflare rehearsal | **Next** |
| Fix BAGIT `data/data` nesting / `list_papers` | Open |
| Europe PMC PDF render outage (upstream) | Open / external |

## 2026-07-16 — P3 adapter outline + tests for review

**User:** outline how to build adapter; show tests for review before proceeding.

- Plan: `docs/demo/climateinsight_manifest_adapter_plan.md`
- ClimateInsight outline: `../ClimateInsight/docs/manifest_adapter_outline.md`
- Tests + fixtures written under `../ClimateInsight/backend/tests/` (skip until modules exist)
- **Adapter implementation not started** — awaiting approval of tests

## 2026-07-16 — P3 adapter implemented on ClimateInsight filestore

**User:** implement adapter now on local filestore.

- Added `ClimateInsight/backend/ingest/manifest_ingest/`
- Extended `Chunk` + Chroma metadata; `ingest.py --manifest`
- **Tests: 14 passed**

## 2026-07-16 — P3 closed; next is P4

**User:** confirm P3 finished; document status before commit / end session.

- **P3 complete** on ClimateInsight local filestore (adapter + 14/14 tests).
- Outline updated: `../ClimateInsight/docs/manifest_adapter_outline.md`
- **Next phase: P4** — rehearse ingest of a real (non-empty) `chatbot_manifest.json`, run RAG, Cloudflare Quick Tunnel dry run.
- Still open in parallel: manual review + re-export; **P2** encyclopedia glue.

---

*Append new dated sections below this line.*
