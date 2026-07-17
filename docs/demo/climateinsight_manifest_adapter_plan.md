# Plan: ClimateInsight adapter for semantic_corpus manifests

**Date:** 2026-07-16 (system date of generation)  
**Status:** **Implemented** (P3) — 14/14 tests passing on ClimateInsight filestore; see `../ClimateInsight/docs/manifest_adapter_outline.md`  
**Repos:** ClimateInsight (primary); for P4 demo, semantic_corpus export must supply a non-empty `chatbot_manifest.json`

Related contract: [chatbot_export_contract.md](../chatbot_export_contract.md)

---

## 1. What the adapter does

```
chatbot_manifest.json
        │
        ▼
  load + validate
        │
        ▼
  for each paper: load text (xml_path → JATS text, else abstract)
        │
        ▼
  Sections → existing chunk_records() → Chunk dicts
        │
        ▼
  ChromaDB (with paper citation metadata)
```

ClimateInsight today only does: one IPCC HTML → `parse_html` → chunks.  
The adapter is the missing branch: **manifest → papers → same chunker/index**.

---

## 2. Build steps (implementation order, after test approval)

| Step | Module (proposed) | Responsibility |
|------|-------------------|----------------|
| A | `ingest/manifest_ingest/load_manifest.py` | Read JSON; require `export_version == "1.0"`; return dict |
| B | `ingest/manifest_ingest/text_loader.py` | Prefer `xml_path` file; else `abstract`; skip/error if neither |
| C | `ingest/manifest_ingest/jats_to_sections.py` | Minimal JATS: body paragraphs → `Section` list; fallback one section from abstract |
| D | `ingest/manifest_ingest/build_from_manifest.py` | Orchestrate A–C; call existing `chunk_records`; prefix `chunk_id` with `source_id`; attach `citation_label`, `doi`, `pmcid` |
| E | `ingest/ingest.py` | Add `--manifest PATH`; keep default IPCC HTML path when omitted |
| F | `vectorstore/indexer.py` | Persist new metadata fields on Chroma chunks |

**Reuse:** `chunker.chunk_records`, `models.Section` / `Chunk`, `ingest_chunks`.  
**Do not** parse `review_table.json` in ClimateInsight — review decisions stay in semantic_corpus; only the **manifest** is ingested.

---

## 3. Prerequisites on semantic_corpus side

1. Papers marked `include` in review table.  
2. `export_corpus_for_chatbot` → non-empty `chatbot_manifest.json`.  
3. `xml_path` values must point at real files (may need BAGIT path fix or query-dir export).

---

## 4. Tests for review

Proposed tests live under `ClimateInsight/backend/tests/`. They define the contract; they **skip** (via `importorskip`) until the adapter modules exist, then must **pass**.

| File | Covers |
|------|--------|
| `conftest.py` | Fixtures: sample JATS XML, rewritten manifest paths |
| `test_manifest_load.py` | Valid load; missing file; bad version; paper_count mismatch |
| `test_manifest_text_loader.py` | Prefer XML; abstract fallback; empty raises; broken path → abstract |
| `test_manifest_jats.py` | Body paragraphs → `Section`; section titles |
| `test_manifest_build.py` | Chunks from manifest; `source_id` prefix; citation metadata; section fields |

**Fixtures:** `backend/tests/fixtures/manifest/sample_paper.xml`, `chatbot_manifest.json`

**Run (from ClimateInsight `backend/`):**

```bash
cd /path/to/ClimateInsight/backend
python -m pytest tests/test_manifest_*.py -v
```

(Requires `pytest`; not yet in ClimateInsight `requirements.txt` — add when implementing.)

---

## 5. Public API the tests expect

```python
# ingest.manifest_ingest.load_manifest
class ManifestError(Exception): ...
def load_manifest(path: Path) -> dict: ...

# ingest.manifest_ingest.text_loader
class TextLoadError(Exception): ...
def load_paper_text(paper: dict) -> tuple[str, str]:  # (text, "xml"|"abstract")

# ingest.manifest_ingest.jats_to_sections
def jats_file_to_sections(path: Path) -> list[Section]: ...

# ingest.manifest_ingest.build_from_manifest
def build_chunks_from_manifest(
    manifest_path: Path, *, chunk_size: int, overlap: int
) -> list:  # Chunk or dict with chunk_id, text, section, section_title,
            # source_id, citation_label, doi, pmcid
```

---

## 6. Decision gate

1. Review this outline and the test files.  
2. Approve → implement modules A–F until tests pass.  
3. Then wire live `ocean_heatwaves_2026` manifest (after includes + export).
