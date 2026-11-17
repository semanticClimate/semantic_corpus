# Module — Phrase extraction and bipartite knowledge graphs

**Logical module:** `phrases_kg`  
**Package:** `semantic_corpus.phrases_kg`  
**JOSS focus:** separate paper theme; code stays **in this repo**  
**Owner focus:** Neel Kumar + Anusha  
**Co-authors (all papers):** Renu Kumari, Peter Murray-Rust  
**Spec:** [`MODULE_SPEC.md`](../../../semantic_corpus/MODULE_SPEC.md) · **Metadata:** `semantic_corpus/phrases_kg/module.yaml`

---

## Purpose

From an **already ingested** corpus (BagIt or flat workdir), extract **lightweight phrases**, build **bipartite paper↔term structure**, and support transparent KG views—including paths toward **figure captions** and related txt2phrases-style methods—without owning ingest or chatbot UI.

---

## In scope

- Cluster-review steps after a corpus exists:  
  - **Step 2** phrase extraction + caches (`cluster_review/step2.py`, editable `lists/`)  
  - **Step 3** bipartite clusters (`step3.py`)  
  - **KG** assembly and HTML/server (`kg.py`, `kg_server.py`)  
- Lightweight approaches (YAKE/TF-IDF and successors); figure-caption and txt2phrases directions as they land  
- Pipeline steps that orchestrate phrases → clusters → kg  
- Optional UI (`apps/cluster_review/`) as a *demo*, not the corpus module’s JOSS core  
- Tests with real mini fixtures; network encyclopedia calls gated like other live tests  

---

## Out of scope

| Belongs elsewhere | Module |
|-------------------|--------|
| Search/download/BagIt | [corpus](../corpus/overview.md) |
| Repository scrapers (GS and others) | [repositories](../repositories/overview.md) |
| Full encyclopedia content system | Sibling `encyclopedia` + bridge hooks |
| Chatbot / RAG product | Export bridge + external apps |

---

## Boundaries

- **Input:** corpus workdir + review table / packets produced by `corpus` (or repositories via the same contracts).  
- **Output:** phrase indexes, cluster graphs, `kg/` artefacts—not a second bag format.  
- Must not reimplement EPMC download inside phrase code.  
- Optional install extra `[kg]` / `[cluster]` for sklearn, networkx, yake, streamlit.  

---

## Related bridges

- **Encyclopedia:** `encyclopedia.py` / disambiguation / HTML writers attach wiki/Wikidata labels onto retained phrases.  
- **Chatbot:** may consume KG or review exports later; ownership of chat UX remains outside this module.  

---

## JOSS claim (draft one-liner)

Lightweight phrase extraction and bipartite paper–term graphs turn a personal BagIt corpus into inspectable knowledge-graph artefacts without black-box embedding pipelines.
