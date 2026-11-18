# Module — Corpus ingest and BagIt

**Logical module:** `corpus`  
**Package:** `semantic_corpus.corpus`  
**JOSS focus for this repository:** yes — primary  
**Owner focus:** Renu Kumari  
**Co-authors (all papers):** Renu Kumari, Peter Murray-Rust  
**Spec:** [`MODULE_SPEC.md`](../../../semantic_corpus/MODULE_SPEC.md) · **Metadata:** `semantic_corpus/corpus/module.yaml`

---

## Purpose

Turn an open-literature **query** (and related intakes) into a **user-owned, preservation-ready corpus**: search → download → metadata → optional **BagIt** layout, with a **review table** as a quality gate—not as the full science product.

---

## In scope

- Corpus create / open (`core/`, `CorpusManager`)  
- Ingest from pygetpapers-style dirs, query outputs, local PDFs (`ingestion/`)  
- BagIt packing and path contracts (`storage/`)  
- Primary OA repositories: Europe PMC (+ diagnostic/preflight), optionally OpenAlex  
- CLI: `cli.py`, `cli_pygetpapers.py`  
- Review table build/export as **ingest QA** (`corpus_review/` workflow/table)  
- Thin export toward chatbot (`export/` is a *bridge*; see modules README)  
- Offline tests with **real** fixture files; live EPMC only with `SC_LIVE_API=1`  

---

## Out of scope (other modules)

| Belongs elsewhere | Module |
|-------------------|--------|
| SciELO / Redalyc / CONICET / LA scrapers | [repositories](../repositories/overview.md) |
| YAKE/TF-IDF phrases, bipartite clusters, KG HTML | [phrases_kg](../phrases_kg/overview.md) |
| Wikipedia encyclopedia HTML content | Encyclopedia bridge + sibling package |
| Chat UI / RAG | Chatbot bridge + external apps |

---

## Public contracts to protect

1. **Stable paper IDs** and filename stems (`repositories/_ids.py`).  
2. **BagIt / flat workdir layout** documented for resume and demos.  
3. **Review-table columns** vocabulary (`corpus_review/constants.py`).  
4. **No mocks** in tests that claim ingest behaviour ([coding_style.md](../../coding_style.md) §0).  

Downstream modules should consume bags/review tables via these contracts, not by scraping EPMC internals.

---

## Docs and examples that serve this module

- BagIt / ingest / EPMC resume tutorials under `docs/` and `docs/tutorials/`  
- Minimal examples: create corpus; search+download; validate bag (trim excess examples over time)  
- Config: one or two YAML pilots (not every topic harvest)

---

## JOSS claim (draft one-liner)

*semantic_corpus* (`corpus`) is an open, scriptable substrate for building and incrementally extending personal scholarly corpora—from declarative ingest and legacy-to-semantic conversion through BagIt packaging and para/caption indexing—so downstream research software can share one input/output contract.

Full JOSS framing (statement of need, complexity, series): [joss_presentation.md](joss_presentation.md).
