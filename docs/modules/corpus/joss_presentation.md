# Presenting `corpus` to JOSS

**Date:** 2026-11-17  
**Module:** [`corpus`](overview.md) (`semantic_corpus.corpus`)  
**Role in series:** core paper; other modules may use corpus I/O **or** run standalone  
**Audience:** authors drafting the JOSS paper and sibling module papers

This note records how we intend to present **corpus** as a standalone JOSS submission and as the substrate for a series (repositories, phrases_kg, encyclopedia, chatbot).

---

## Scope claimed for the corpus paper

The corpus module (this JOSS theme) provides:

1. **Generic declarative ingest** — config-driven intake into a stable corpus layout.  
2. **Semantification of content** — including legacy → semantic paths (e.g. PDF, DOCX).  
3. **Indexing** down to **paragraph and caption** level.  
4. **Incremental addition** via **doit** (and hooks for downstream processing by other modules).

Plus the existing preservation/QA face: BagIt-compatible trees, stable paper IDs, review table as ingest QA.

**Out of scope for the corpus SoN** (sibling papers / consumers only): SciELO/GS adapter depth as the main story, phrase/KG algorithms, encyclopedia content systems, chatbot UX. Mention them only as modules that can **consume** the corpus contract.

---

## Statement of need (draft spine)

JOSS requires a labeled **Statement of need** that states the problem, the audience, and relation to related work.

### Problem

Researchers building personal or project corpora from open literature lack a **reusable, preservation-oriented substrate**. Intake is often ad hoc (PDFs, DOCX, repository dumps); layout and IDs are unstable; conversion to usable text is opaque; and re-runs redo work instead of incrementally updating. Downstream tools (KG, encyclopedic enrichment, chat/RAG) then each reinvent ingest.

### Audience

Domain scientists and research software engineers who need **citable, inspectable corpora**—not another black-box search UI—especially open-science / climate groups who already use pygetpapers-style harvests and want BagIt-ready trees with transparent QA.

### Gap / related work

Downloaders and search APIs (Europe PMC, OpenAlex, pygetpapers, Zotero, …) get documents onto disk; NLP/KG stacks assume clean text already. Few tools combine **declarative multi-source ingest**, **semantification of legacy formats**, **stable IDs + BagIt**, **paragraph/caption-level indexing**, and **incremental task orchestration** so other modules can plug in without owning corpus layout.

### One-sentence claim

*semantic_corpus* (`corpus`) is an open, scriptable substrate for building and incrementally extending personal scholarly corpora—from declarative ingest and legacy-to-semantic conversion through BagIt packaging and para/caption indexing—so downstream research software can share one input/output contract.

---

## Complexity: is it enough for a standalone JOSS paper?

**Verdict:** With the four pillars above (declarative ingest, semantification, para/caption indexing, incremental `doit`), **corpus is comfortably enough for a standalone JOSS paper**, and is the right first paper in the series. A thinner “EPMC → BagIt wrapper” claim would be riskier under JOSS guidance against minor utilities / thin API clients.

| JOSS lens | Assessment for planned corpus |
|-----------|-------------------------------|
| Substantial scholarly effort | Strong if the four pillars ship as feature-complete, tested, and documented—not aspirational TODOs. Multi-month public history and multi-author work strengthen the case. |
| Not a thin wrapper | Safe if the scholarly contribution is the **corpus substrate** (contracts, semantification, indexing, incremental orchestration), not “calls Europe PMC.” |
| Standalone usable | Required: install → declarative config → ingest/convert → BagIt + review QA → index → resume with `doit`, **without** installing repositories / phrases_kg / chatbot. |
| Series-friendly | Sibling papers cite corpus as optional I/O; each sibling must also run **standalone** on its own inputs so editors do not see one paper chopped five ways. |

**Good enough for a paper outline now; good enough for submission when** those capabilities are demonstrable in a short tutorial with **real fixtures** (no mocks), plus a **Software design** section explaining why BagIt + para/caption index + `doit` are the abstraction.

**Weaker if submission still mainly shows** search/download + review table only—then either strengthen design/impact narrative or wait until semantification, indexing, and incremental add are first-class.

JOSS also expects (current paper format): Summary, Statement of need, State of the field, Software design, Research impact statement, AI usage disclosure. See [JOSS paper format](https://joss.readthedocs.io/en/latest/paper.html) and [review criteria](https://joss.readthedocs.io/en/latest/review_criteria.html).

---

## Series presentation

| Paper / module | Relation to corpus |
|----------------|--------------------|
| **corpus** (core) | Self-contained substrate; citable alone |
| **repositories** | May harvest into corpus contracts **or** stand alone |
| **phrases_kg** | May consume BagIt/index **or** stand alone on a conforming workdir |
| **encyclopedia** | Enrichment bridge / sibling; optional after a corpus exists |
| **chatbot** | Export/RAG consumer; corpus claims a **stable export**, not a chat product |

**Sibling SoN tip:** “May consume a *semantic_corpus* BagIt/index, **or** operate on a standalone workdir conforming to the same contracts.” That keeps corpus as the core citation while leaving each sibling independently reviewable.

---

## Related docs

- Module overview: [overview.md](overview.md)  
- One-repo module policy: [../README.md](../README.md)  
- Ownership table: [../../repo_responsibilities.md](../../repo_responsibilities.md)  
- Cleanup / keep list: [../../joss_cleanup_plan.md](../../joss_cleanup_plan.md)  
- Package contract: [`MODULE_SPEC.md`](../../../semantic_corpus/MODULE_SPEC.md)
