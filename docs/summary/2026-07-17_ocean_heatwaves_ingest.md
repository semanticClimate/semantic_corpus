# Summary: ocean_heatwaves_2026 live ingest into ClimateInsight

**Date:** 2026-07-17 (system date of generation)  
**Topic:** Ingest bundle handoff and first successful `--manifest` run  
**Corpus:** `ocean_heatwaves_2026`

---

## Outcome

The semantic_corpus → ClimateInsight pipeline is **working end-to-end** for the curated subset:

- **12 included papers** exported to `chatbot_manifest.json`
- Bundle copied to `ClimateInsight/backend/tests/fixtures/ocean_heatwaves_2026/`
- **314 chunks** indexed in ChromaDB (embedding model `all-MiniLM-L6-v2`)

This completes the first major step of **P4** (live ingest). RAG chat smoke and Cloudflare tunnel remain.

---

## Review curation

| Status | Count |
|--------|-------|
| include | 12 |
| exclude | 2 |
| review | 36 |

Canonical review file: `tests/fixtures/ocean_heatwaves_2026/review/review_table.edited.json`

---

## Key artefacts

| Location | File |
|----------|------|
| semantic_corpus | `tests/fixtures/ocean_heatwaves_2026/chatbot_manifest.json` |
| semantic_corpus | `temp/exports/ocean_heatwaves_2026/chatbot_manifest.json` |
| ClimateInsight | `backend/tests/fixtures/ocean_heatwaves_2026/chatbot_manifest.json` |

---

## Code fix

`build_citation_label` in `semantic_corpus/export/chatbot_export.py` now formats Europe PMC author dicts correctly for UI citations.

---

## Still open

- RAG smoke test (Ollama + citations)
- Cloudflare Quick Tunnel dry run
- BAGIT `data/data/` nesting (standard export still blocked)
- P2 encyclopedia glue

---

## Related docs

- [Full session record](../records/2026-07-17_ocean_heatwaves_ingest.md)
- [Progress log](../demo/ocean_heatwaves_progress.md)
- [Position review (morning)](2026-07-17_ocean_heatwaves_position.md)
