# JOSS series strategy — modules, owners, community evidence

**Date:** 2026-11-17  
**Source discussion:** [discussions/CEVOpen transcript_2026-11-17_10.01.38.txt](../discussions/CEVOpen%20transcript_2026-11-17_10.01.38.txt) (Peter Murray-Rust + Renu Kumari)  
**Related:** [modules/README.md](modules/README.md) · [modules/corpus/joss_presentation.md](modules/corpus/joss_presentation.md) · [repo_responsibilities.md](repo_responsibilities.md) · [authors_202611.md](authors_202611.md) · [corpus interop governance](../semantic_corpus/corpus/docs/team_interop_governance.md)

This document outlines the agreed strategy for publishing **semantic_corpus** work as a **series of JOSS papers**, with **corpus** as the core substrate and sibling modules that can consume corpus contracts **or** stand alone.

---

## 1. Why JOSS (and why a series)

- Prefer JOSS over high-cost conventional venues; pygetpapers already published there; overhead is lower and review is constructive / day-scale once in review.
- **Primary plan:** several **single-purpose, standalone** papers (about **five** themes), submitted **sequentially**.
- **Fallback if editors insist on one product paper:** one large paper with a large author list (~20), still documenting the same modules.
- We will **write to JOSS editors** to argue that the split is justified (standalone modules + clear contracts), while **starting the technical work now** against JOSS guidelines regardless.

---

## 2. Submodules (logical papers)

One GitHub project for now; separation by **module package + docs + ownership**, not by remotes (unless later agreed).

| # | Module | JOSS role | What it owns | Standalone? |
|---|--------|-----------|--------------|-------------|
| 1 | **`corpus`** | **Core / first paper** | BagIt layout; ingest from literature search **and** static resources; **doit** incremental pipeline; semantification; semantic chunks (paragraphs, figures, tables); typed objects with clear IDs; textual search; declarative YAML/JSON; externalized HTML/JS where practical | Yes — enough to build and update a personal corpus |
| 2 | **`repositories`** | Sibling | Literature-repository adapters (EPMC, OpenAlex, CONICET, SciELO, Redalyc, …); emphasis on **Global South** / non-EN sources; declarative download templates outside core code | Yes — adapters + harvest; may write into corpus contracts |
| 3 | **`phrases_kg`** | Sibling | Phrase extraction and knowledge-graph / bipartite structure | Yes — or consume corpus BagIt/index |
| 4 | **encyclopedia** | Sibling / bridge | Encyclopedic enrichment (name may change) | Yes — or attach after a corpus exists |
| 5 | **chatbot** | Sibling / bridge | Chat / export / RAG-facing product (UI may live elsewhere; this repo keeps export contracts) | Yes — or consume corpus export |

**Corpus principles (from the discussion, for design + JOSS Software design):**

1. Get information in → make it **semantic** → keep it **up to date** with **doit** (new material updates; incomplete material is completed).  
2. Semantic units are meaningful document chunks (paragraphs, figures, tables, …) with **type + ID** (and preferably search).  
3. Prefer **declarative** config (YAML/JSON) and **external** presentation assets so contributors edit templates without patching core Python.  
4. Sibling modules share **contracts** (IDs, BagIt/workdir, indexes, export), not copies of ingest internals.

**Corpus JOSS one-liner (unchanged intent):** open, scriptable substrate for personal scholarly corpora — declarative ingest, legacy→semantic conversion, BagIt, para/caption-level indexing, incremental `doit` — so other tools share one I/O contract. Detail: [modules/corpus/joss_presentation.md](modules/corpus/joss_presentation.md).

---

## 3. Owners and meeting pattern

Co-authors on the **corpus** paper at minimum: **Renu Kumari**, **Peter Murray-Rust**. Corpus may still list many additional contributors (interns, case-study authors, etc.).

| Module | Focus owners (working) | Meeting pattern |
|--------|------------------------|-----------------|
| **corpus** | Renu Kumari (+ PMR) | **Weekly** — template for how other submodule groups run |
| **repositories** | Larisa Beni (tentative; learning-focused ownership) | Weekly submodule meeting; PMR attends; Renu welcome |
| **phrases_kg** | Neel Kumar + Anusha | Weekly submodule meeting; PMR attends |
| **encyclopedia** | TBD | Schedule when lead named |
| **chatbot** | Aleena / Anusha (and related ClimateInsight work as applicable) | Schedule with leads |

**Operating rules:**

- Not everyone joins every submodule; **owner + PMR (+ optional Renu)** is enough for a working session.  
- Submodule days are chosen around exams / time zones (Thursday group sync remains the cross-cutting checkpoint).  
- New repository partnerships: prefer partners who bring **both a repository and a volunteer** (builds critical mass). Outreach planned toward SciELO, Redalyc, and other open archives; university thesis collections remain of interest where access is realistic.  
- OpenAlex completion called out as in-scope for repositories/corpus intake work.

---

## 4. Community involvement — how we evidence it for JOSS

JOSS reviewers ask whether submitting authors made major contributions, whether there is **community engagement**, **sustained open development**, and clear **research impact**. Our practice does not always map 1:1 onto “many commits on `main` by every named author,” especially with **3-month internships** where PMR often merges/commits after group design.

### 4.1 Recordings and discussion transcripts

**Weekly (and submodule) meetings are first-class project artefacts.**

- Save transcripts under `discussions/` (example: this strategy’s source transcript).  
- Feed transcripts into docs / agent sessions so decisions become **written principles** (module specs, SoN, ownership tables)—not only chat memory.  
- For JOSS / editor correspondence, cite the **corpus of recordings + dated docs** as evidence that:
  - design and scope are **communal**, not solitary AI or solitary maintainer output;
  - named owners (Renu, Larisa, Neel, Anusha, …) participate in **recurring** technical direction;
  - internship cohorts contribute through **structured sessions**, even when git authorship is asymmetric.

Suggested author-response phrasing (adapt as needed):

> We meet regularly (weekly core; submodule sessions with module owners). Session transcripts are archived in the repository under `discussions/` and used to update `docs/`. Commit history on `main` is often curated by the technical lead for internship-scale contributions; substantive authorship is evidenced by named branches, module ownership, and the discussion archive.

### 4.2 Git history that JOSS already understands

- Prefer **named long-lived branches** for contributor credit (JOSS has asked whether Git history shows significant contribution).  
- Keep [authors_202611.md](authors_202611.md) (and successors) as a human map from people → branches → themes.  
- Branches need not all be merged to prove participation; they must remain **discoverable in history**.

### 4.3 Other impact / engagement signals

| Signal | Use in Research impact / community answers |
|--------|-----------------------------------------------|
| Multi-year open development of semantic_corpus / related tools | Sustained development |
| Talks / CoPs / community presentations (e.g. Fiske and related forums) | Research impact / engagement where citations are still thin |
| Tutorials, declarative configs, real fixtures (no mocks) | Reuse + functional claims |
| CI, tests, coverage, README install + citation | Reviewer checklist hygiene |
| AI usage log in `docs/` | Required AI disclosure; everyone records prompts/requests used for paper or substantial code |

**Weakest JOSS axis today:** formal **research impact** (external citations). Compensate with talks, reproducible tutorials, and clear adoption path for sibling modules—not with inflated scope.

---

## 5. Authorship and credit model

| Situation | Approach |
|-----------|----------|
| Corpus paper | Renu + PMR as lead co-authors; broader contributor list from sustained participants |
| Sibling papers | Module owners as focus leads; Renu + PMR typically co-authors across the series |
| Intern / short stay | Credit via branch + transcript + CONTRIBUTING / authors snapshot; merge policy stays quality-gated |
| If JOSS forces a single paper | Large multi-author list reflecting the whole community |

---

## 6. Near-term actions (from the discussion)

1. Keep developing **corpus** to JOSS guidelines (SoN, design, examples, tests).  
2. Contact JOSS editors about **series vs single paper**.  
3. Stand up **submodule weekly** slots (Larisa / repositories; Neel+Anusha / phrases_kg; …).  
4. Continue archiving **CEVOpen (and related) transcripts** into `discussions/` and summarizing into `docs/`.  
5. Everyone logs **AI assistance** into docs for disclosure.  
6. Renu to help **smoke-test** main after recent merges.  
7. Strengthen CI / coverage where reviewer checklists will demand it.

---

## 7. How this file relates to recordings

| Artefact | Role |
|----------|------|
| `discussions/*transcript*.txt` | Primary evidence of communal decision-making |
| This strategy doc | Stable summary for JOSS authors and editors |
| `docs/modules/*/overview.md` + `module.yaml` | Technical face of each submodule |
| `docs/modules/corpus/joss_presentation.md` | Corpus-specific SoN / complexity argument |
| `docs/authors_*.md` | People ↔ git branches |

When preparing the JOSS submission or editor letter, point reviewers at **§4** of this document and at the linked transcript dated **2026-11-17**.
