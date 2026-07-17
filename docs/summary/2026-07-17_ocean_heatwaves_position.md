# Summary: ocean_heatwaves_2026 demo position review

**Date:** 2026-07-17 (system date of generation)  
**Topic:** Which phases are complete; what remains before chatbot ingest  
**Corpus:** `ocean_heatwaves_2026`

---

## Phase status

| Phase | Scope | Status |
|-------|--------|--------|
| **P0** | Config + proposal + runbook | ✅ Done |
| **P1** | Harvest, review table, BAGIT ingest, PRISMA, export stub | ✅ Mostly done (gaps below) |
| **P2** | Encyclopedia from curated corpus | ❌ Not started |
| **P3** | ClimateInsight manifest adapter (`--manifest`) | ✅ Done (code + 14 tests) |
| **P4** | Live ingest rehearsal + RAG smoke + Cloudflare tunnel | ❌ Not started |

---

## What exists today

### semantic_corpus (`ocean_heatwaves_2026`)

| Artefact | State |
|----------|--------|
| Config | `config/ocean_heatwaves_2026.yaml` |
| Query output | `temp/queries/ocean_heatwaves_2026/` — 50 hits, 49 XML, 10 PDF |
| Review table | 50 rows; **all `review`** (no `include` / `exclude` yet) |
| BAGIT corpus | `corpora/ocean_heatwaves_2026/` (nested `data/data/` path quirk) |
| Chatbot export | `temp/exports/ocean_heatwaves_2026/chatbot_manifest.json` — **0 papers** |

Acquisition used **semantic_corpus Europe PMC**, not pygetpapers.

### ClimateInsight

| Artefact | State |
|----------|--------|
| `backend/ingest/manifest_ingest/` | ✅ Implemented |
| `python -m ingest.ingest --manifest …` | Ready |
| Live ingest of ocean heatwaves papers | **Not done** |
| Cloudflare tunnel demo | **Not done** (P4) |

---

## P3 vs “ingest into chatbot”

**P3** delivered the **adapter** (manifest → JATS/abstract → chunks → Chroma) and unit tests on fixtures.

It did **not** run end-to-end ingest of real `ocean_heatwaves_2026` papers.

The **next operational step** is the first use of that adapter with a **non-empty** manifest — the start of **P4**, not a new phase.

---

## Recommended sequence (before P4 Cloudflare)

1. **Manual review** — set `include` / `exclude` in the review table (target ~25–35 includes for demo).
2. **Export manifest** — `chatbot_manifest.json` with valid `xml_path` for included papers (may need BAGIT path fix or query-dir export).
3. **Ingest ClimateInsight** — `ingest.ingest --manifest <path>`.
4. **Smoke RAG** — backend + frontend; domain questions; check citations.
5. **P4** — Cloudflare Quick Tunnel (`scripts/inject-tunnel.py`).
6. **P2** (parallel or later) — encyclopedia glue.

---

## Blockers

| Issue | Impact |
|-------|--------|
| No `include` rows | Export stays empty |
| BAGIT `data/data/` nesting | `xml_path` in manifest may not resolve |
| ClimateInsight on teammate machines | Needs `manifest_ingest` from local filestore / commit |
| PDF gap (10/50) | Low — adapter uses XML or abstract |

---

## Related docs

- [ocean_heatwaves_progress.md](../demo/ocean_heatwaves_progress.md) — incremental log
- [ocean_heatwaves_proposal.md](../demo/ocean_heatwaves_proposal.md) — full plan
- [climateinsight_manifest_adapter_plan.md](../demo/climateinsight_manifest_adapter_plan.md)
- [chatbot_export_contract.md](../chatbot_export_contract.md)
