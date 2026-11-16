# Summary: ocean_heatwaves_2026 demo (2026-07-16)

**Date:** 2026-07-16 (system date of generation)  
**Topic:** End-to-end semantic_corpus demo — marine heatwaves & ocean currents  
**Status:** Proposal + P0 + P1 + P3 complete; PDFs partial (10/50); manual review, P2, and **P4 next**

## What we set out to do

Show query → download → review table → encyclopedia → ClimateInsight RAG → Cloudflare in one coherent demo corpus, distinct from `climate_anxiety_2026`.

## What we delivered today

1. **Docs + config (P0)** under `docs/demo/` and `config/ocean_heatwaves_2026.yaml`.
2. **Harvest (P1)** of 50 Europe PMC hits; 49 XML; review table built.
3. **PDF fix + re-run:** 10 publisher PDFs on disk; review table `has_pdf` updated.
4. **Incremental documentation:** progress log, record, this summary.

## Tooling clarification

Search/download used **semantic_corpus’s Europe PMC adapter**, **not pygetpapers**.

## Blockers / honesty

- Europe PMC PDF render endpoint largely broken (404) on this date.
- BAGIT nesting (`data/data/`) breaks `list_papers` / empty chatbot export until fixed.
- No papers marked `include` yet → chatbot manifest paper_count = 0 by design.

## Where to read more

| Doc | Use |
|-----|-----|
| [docs/demo/ocean_heatwaves_progress.md](../demo/ocean_heatwaves_progress.md) | Append-only timeline |
| [docs/records/2026-07-16_ocean_heatwaves_demo.md](../records/2026-07-16_ocean_heatwaves_demo.md) | Technical record |
| [docs/demo/ocean_heatwaves_demo.md](../demo/ocean_heatwaves_demo.md) | Commands |
| [docs/demo/ocean_heatwaves_proposal.md](../demo/ocean_heatwaves_proposal.md) | Full plan |

## Immediate next steps

1. Serve review table; mark ~25–35 `include`.
2. Fix or work around corpus path nesting; re-export a non-empty manifest.
3. **P4:** ingest that manifest in ClimateInsight, RAG smoke-test, Cloudflare dry run.
4. Optional in parallel: **P2** (encyclopedia) when approved.
