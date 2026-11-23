# Module — Corpus ingest and BagIt

**Logical module:** `corpus`  
**Package:** `semantic_corpus.corpus`  
**JOSS focus for this repository:** yes — primary  
**Owner focus:** Renu Kumari  
**Co-authors (all papers):** Renu Kumari, Peter Murray-Rust  
**Spec:** [`MODULE_SPEC.md`](../../../semantic_corpus/MODULE_SPEC.md) · **Metadata:** `semantic_corpus/corpus/module.yaml`

---

## Purpose

Provide a **standalone personal/project corpus substrate**: a BagIt filestore-as-database with declarative, human-limited ingest, skip-satisfied incremental processing (`doit`-like), cleaning/semanticisation to structured HTML (sections, paragraphs, figures/tables + captions), and an HTML review table for Browse / Read / Delete / regex search.

Full functionality and usage scenarios: **[design.md](design.md)**.

---

## In scope

- Corpus create / open and BagIt (or flat→BagIt) layout contracts  
- Schema-light ingest (queries, closed sets, local files; optional Zotero as source)  
- Incremental Create / Rerun with skip-satisfied entries  
- Declarative cleaners → semantic HTML with stable chunk IDs  
- Ingest hooks + EPMC example for `repositories` adapters  
- HTML review table as ingest QA / curation  
- Thin export bridge toward chatbot (not chat UX)  
- Offline tests with **real** fixtures; live network only with `SC_LIVE_API=1`  

---

## Out of scope (other modules)

| Belongs elsewhere | Module |
|-------------------|--------|
| SciELO / Redalyc / CONICET / LA scrapers | [repositories](../repositories/overview.md) |
| YAKE/TF-IDF phrases, bipartite clusters, KG HTML | [phrases_kg](../phrases_kg/overview.md) |
| Wikipedia encyclopedia HTML content | Encyclopedia bridge + sibling package |
| Chat UI / RAG | Chatbot bridge + external apps |
| Bibliographic discovery UX | Zotero (interop only; see [design.md](design.md) §8.4) |

---

## Public contracts to protect

1. **Stable paper IDs** and filename stems.  
2. **BagIt / workdir layout** documented for resume and demos.  
3. **Review-table columns** vocabulary (`corpus_review/constants.py`).  
4. **No mocks** in tests that claim ingest behaviour ([coding_style.md](../../coding_style.md) §0).  

Downstream modules should consume bags/review tables / semantic HTML via these contracts.

---

## Docs

- **Design + user scenarios:** [design.md](design.md)  
- **User narratives (Statement of need):** [user_narratives.md](user_narratives.md)  
- **Sibling schematic:** [siblings.md](siblings.md)  
- **JOSS framing:** [joss_presentation.md](joss_presentation.md)  
- **Interfaces / team governance** (`corpus/` as hub): [`corpus/docs/team_interop_governance.md`](../../../semantic_corpus/corpus/docs/team_interop_governance.md)  
- **Submodule guidelines:** [`corpus/docs/submodule_guidelines.md`](../../../semantic_corpus/corpus/docs/submodule_guidelines.md)  
- **Text block vocabulary:** [`corpus/docs/definitions_text_block.md`](../../../semantic_corpus/corpus/docs/definitions_text_block.md)  
- **Document platform** (semantify/section without BagIt): [`corpus/docs/document_platform.md`](../../../semantic_corpus/corpus/docs/document_platform.md)  
- **I/O types + storage:** [`corpus/docs/types_io_storage.md`](../../../semantic_corpus/corpus/docs/types_io_storage.md)  
- Package docs index: [`corpus/docs/README.md`](../../../semantic_corpus/corpus/docs/README.md)  
- Tutorials under `docs/` and `docs/tutorials/` (trim excess over time)  
- Config: one or two YAML pilots (not every topic harvest)

---

## JOSS claim (draft one-liner)

*semantic_corpus* (`corpus`) is an open, scriptable substrate for building and incrementally extending personal scholarly corpora—from declarative ingest and legacy-to-semantic conversion through BagIt packaging and para/caption indexing—so downstream research software can share one input/output contract.
