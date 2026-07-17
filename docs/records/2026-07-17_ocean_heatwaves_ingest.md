# Record: ocean_heatwaves_2026 ingest bundle + ClimateInsight live ingest

**Date:** 2026-07-17 (system date of generation)  
**Status:** P4 started — manifest export + live ingest ✅; RAG smoke + Cloudflare pending  
**Corpus:** `ocean_heatwaves_2026`

**Related:**

- [Progress log (incremental)](../demo/ocean_heatwaves_progress.md)
- [Position review](../summary/2026-07-17_ocean_heatwaves_position.md)
- [Session summary](../summary/2026-07-17_ocean_heatwaves_ingest.md)
- [Chatbot export contract](../chatbot_export_contract.md)
- ClimateInsight: `backend/tests/fixtures/ocean_heatwaves_2026/`

---

## Goal this session

1. Copy a **ClimateInsight-ready ingest bundle** from semantic_corpus fixtures.
2. Generate up-to-date **`chatbot_manifest.json`** files (12 included papers).
3. Hand off to ClimateInsight for live Chroma ingest (user runs in `.venv`).

---

## Review table (team-curated)

Source: `tests/fixtures/ocean_heatwaves_2026/review/review_table.edited.json`

| Status | Count |
|--------|-------|
| `include` | 12 |
| `exclude` | 2 |
| `review` | 36 |

All 12 includes have matching XML in the fixture directory. Six includes also have PDF.

**Included PMCIDs:** PMC10468509, PMC11128013, PMC11580339, PMC12980662, PMC9613989, PMC10011364, PMC10808424, PMC11427463, PMC11733174, PMC7653907, PMC8294506, PMC9135278

**Excluded PMCIDs:** PMC10682185, PMC12675643

**Note:** Review viewer save initially wrote to Downloads; edited table was recovered by manual copy into fixtures.

---

## Ingest bundle layout

### semantic_corpus (source fixture)

`tests/fixtures/ocean_heatwaves_2026/`

- Flat `PMC*.xml` / `PMC*.pdf` (copied from query harvest)
- `search_results.json`, `query_run.json`
- `review/review_table.edited.json`, `review/review_table.orig.json`
- **`chatbot_manifest.json`** — paths point at this fixture dir

Also refreshed: `temp/exports/ocean_heatwaves_2026/chatbot_manifest.json`

### ClimateInsight (handoff copy)

`ClimateInsight/backend/tests/fixtures/ocean_heatwaves_2026/`

| Item | Count |
|------|-------|
| Papers in manifest | 12 |
| XML files | 12 |
| PDF files | 6 |
| Review table | `review/review_table.edited.json` |
| README | ingest command + provenance |

Manifest `xml_path` / `pdf_path` values are absolute paths under the ClimateInsight fixture directory.

---

## Manifest generation approach

Standard `export_corpus_for_chatbot` against the BAGIT corpus still fails (`list_papers()` → 0) because of nested `data/data/` layout. This session used a **fixture-based export**:

- Filter `review_table.edited.json` for `review_status == include`
- Join metadata/abstracts from `search_results.json`
- Resolve full-text paths from flat fixture layout (`{pmcid}.xml`, `{pmcid}.pdf`)
- Write `chatbot_manifest.json` per [chatbot_export_contract.md](../chatbot_export_contract.md)

---

## Code change (semantic_corpus)

**File:** `semantic_corpus/export/chatbot_export.py`

**Fix:** `build_citation_label` now handles Europe PMC author dicts (not only string authors).

- Before: citation label could embed a raw Python dict repr.
- After: uses `_first_author_display()` → e.g. `Kumar (2023). Analysis of marine heatwaves over the Bay of Bengal during 1982-2021.`

---

## ClimateInsight live ingest (user-run)

Environment: ClimateInsight `.venv` with `chromadb` installed.

```bash
cd backend
python -m ingest.ingest --manifest tests/fixtures/ocean_heatwaves_2026/chatbot_manifest.json
```

### Results

| Metric | Value |
|--------|-------|
| Papers | 12 |
| Chunks created | 314 (per-paper: 22, 28, 33, 26, 26, 30, 31, 18, 32, 29, 24, 15) |
| ChromaDB stored | 314 / 314 |
| Skipped (already stored) | 0 |
| Embedding model | `all-MiniLM-L6-v2` |

### Non-fatal warnings

Chroma telemetry events failed with `capture() takes 1 positional argument but 3 were given` (posthog/chromadb version mismatch). Indexing completed successfully despite these messages.

---

## Phase status after session

| Phase | Status |
|-------|--------|
| P0 | ✅ Done |
| P1 | ✅ Done (harvest + review table; BAGIT nesting still open) |
| P2 | ❌ Not started |
| P3 | ✅ Done (manifest adapter + 14 tests) |
| P4 | **In progress** — live ingest ✅; RAG smoke + Cloudflare pending |

---

## Open items

1. **RAG smoke test** — retrieval + Ollama answer with citations on domain questions.
2. **Cloudflare tunnel** — `python scripts/inject-tunnel.py` from ClimateInsight root.
3. **BAGIT path fix** — so standard `export_corpus_for_chatbot` works without fixture workaround.
4. **Review save UX** — viewer should save to repo path, not Downloads (deferred).
5. **Commit/sync** — ClimateInsight `manifest_ingest` + fixtures may need push for teammates.

---

## Commands reference (next steps)

**Retrieval smoke (ClimateInsight `backend/`):**

```bash
python -c "
from vectorstore import query_chunks
hits = query_chunks('What causes marine heatwaves in the Bay of Bengal?', top_k=3)
for h in hits:
    print(h.get('citation_label', h.get('source_id')), '-', (h.get('text') or '')[:120])
"
```

**Tunnel demo (ClimateInsight repo root):**

```bash
python scripts/inject-tunnel.py
```
