# Module 3 — Phrase extraction and bipartite knowledge graphs

**Logical module:** `phrases_kg`  
**JOSS focus:** separate paper theme; code stays **in this repo**  
**Owner focus:** Neel Kumar  
**Co-authors (all papers):** Renu Kumari, Peter Murray-Rust  

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
- Optional UI (`apps/cluster_review/`) as a *demo*, not Module 1’s JOSS core  
- Tests with real mini fixtures; network encyclopedia calls gated like other live tests  

---

## Out of scope

| Belongs elsewhere | Module |
|-------------------|--------|
| Search/download/BagIt | [ingest_bagit.md](ingest_bagit.md) |
| GS repository scrapers | [global_south.md](global_south.md) |
| Full encyclopedia content system | Sibling `encyclopedia` + bridge hooks |
| Chatbot / RAG product | Export bridge + external apps |

---

## Boundaries

- **Input:** corpus workdir + review table / packets produced by Module 1 (or GS via the same contracts).  
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
