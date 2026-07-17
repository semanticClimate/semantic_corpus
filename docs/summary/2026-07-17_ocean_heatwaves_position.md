# Summary: ocean_heatwaves_2026 demo position review

**Date:** 2026-07-17 (system date of generation)  
**Topic:** Phase status — updated after live ClimateInsight ingest  
**Corpus:** `ocean_heatwaves_2026`

> **Update (same day):** Live ingest complete — see [2026-07-17_ocean_heatwaves_ingest.md](2026-07-17_ocean_heatwaves_ingest.md).

---

## Phase status

| Phase | Scope | Status |
|-------|--------|--------|
| **P0** | Config + proposal + runbook | ✅ Done |
| **P1** | Harvest, review table, BAGIT ingest, PRISMA, export stub | ✅ Mostly done (gaps below) |
| **P2** | Encyclopedia from curated corpus | ❌ Not started |
| **P3** | ClimateInsight manifest adapter (`--manifest`) | ✅ Done (code + 14 tests) |
| **P4** | Live ingest rehearsal + RAG smoke + Cloudflare tunnel | **In progress** — ingest ✅ (314 chunks); RAG + tunnel pending |

---

## What exists today

### semantic_corpus (`ocean_heatwaves_2026`)

| Artefact | State |
|----------|--------|
| Config | `config/ocean_heatwaves_2026.yaml` |
| Query output | `temp/queries/ocean_heatwaves_2026/` — 50 hits, 49 XML, 10 PDF |
| Review table | 12 `include`, 2 `exclude`, 36 `review` — `tests/fixtures/.../review/review_table.edited.json` |
| Fixture bundle | `tests/fixtures/ocean_heatwaves_2026/` — 12 XML, manifests |
| BAGIT corpus | `corpora/ocean_heatwaves_2026/` (nested `data/data/` path quirk — export workaround uses fixtures) |
| Chatbot export | `chatbot_manifest.json` — **12 papers** (fixture paths) |

Acquisition used **semantic_corpus Europe PMC**, not pygetpapers.

### ClimateInsight

| Artefact | State |
|----------|--------|
| `backend/ingest/manifest_ingest/` | ✅ Implemented |
| `python -m ingest.ingest --manifest …` | Ready |
| Ingest bundle | `backend/tests/fixtures/ocean_heatwaves_2026/` |
| Live ingest | ✅ **314 chunks** in ChromaDB (2026-07-17) |
| RAG smoke + Cloudflare tunnel | **Not done** (P4 remainder) |

---

## P3 vs “ingest into chatbot”

**P3** delivered the **adapter** (manifest → JATS/abstract → chunks → Chroma) and unit tests on fixtures.

It did **not** run end-to-end ingest of real `ocean_heatwaves_2026` papers.

The **next operational step** is the first use of that adapter with a **non-empty** manifest — the start of **P4**, not a new phase.

---

## Recommended sequence (remaining P4)

1. ~~Manual review~~ ✅ (12 includes)
2. ~~Export manifest~~ ✅ (fixture-based)
3. ~~Ingest ClimateInsight~~ ✅ (314 chunks)
4. **Smoke RAG** — backend + frontend; domain questions; check citations.
5. **Cloudflare Quick Tunnel** — `scripts/inject-tunnel.py`.
6. **P2** (parallel or later) — encyclopedia glue.

---

## Blockers

| Issue | Impact |
|-------|--------|
| BAGIT `data/data/` nesting | Standard export still broken; fixture workaround in use |
| ClimateInsight on teammate machines | Needs `manifest_ingest` from local filestore / commit |
| PDF gap (10/50) | Low — adapter uses XML or abstract |

---

## Related docs

- [ocean_heatwaves_progress.md](../demo/ocean_heatwaves_progress.md) — incremental log
- [ocean_heatwaves_proposal.md](../demo/ocean_heatwaves_proposal.md) — full plan
- [climateinsight_manifest_adapter_plan.md](../demo/climateinsight_manifest_adapter_plan.md)
- [chatbot_export_contract.md](../chatbot_export_contract.md)
