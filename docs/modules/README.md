# Logical modules — one repository (strong default)

**Date:** 2026-11-16 (system date)  
**Decision:** Keep **one** GitHub project (`semanticClimate/semantic_corpus`). Do **not** create a new repo per JOSS theme unless leads later agree APIs are stable and owners can release independently.  
**Co-authors on all papers:** Renu Kumari, Peter Murray-Rust  

Separation is by **named functionality + ownership + docs**, not by remotes.

---

## Why this default

| Prefer one repo + modules | Avoid many repos (for now) |
|---------------------------|----------------------------|
| One install and one ID/BagIt vocabulary | Version skew and “which combo works?” |
| End-to-end demos stay possible | Five clone/CI/release trains for 3‑month ECRs |
| Clear JOSS *chapters* without fracturing the pipeline | Premature freeze of unstable boundaries |
| Optional install extras can still thin the *core* claim | Duplicate types (`paper_id`, review columns) |

**Split out a theme later only when** it has a stable public API, its own tests/docs, and an owner who can cut a release without breaking ingest.

Full keep/delete context: [joss_cleanup_plan.md](../joss_cleanup_plan.md). Short ownership table: [repo_responsibilities.md](../repo_responsibilities.md).

---

## The four major modules (this folder)

| # | Document | Focus owner | JOSS role |
|---|----------|-------------|-----------|
| 1 | [ingest_bagit.md](ingest_bagit.md) | Renu Kumari | **Primary** software paper for this repo: ingest + BagIt |
| 2 | [global_south.md](global_south.md) | Larisa Beni | Harvest adapters (Redalyc, SciELO, CONICET, …); non-EN |
| 3 | [phrases_kg.md](phrases_kg.md) | Neel Kumar | Phrase extraction, bipartite clusters/KG, lightweight methods |
| 4 | *(bridges — see below)* | Encyclopedia TBD; chatbot Aleena + Anusha | Thin hooks/export here; UIs/content may live elsewhere |

Modules **1–3** are full in-repo functionalities. **Encyclopedia** and **chatbot** stay **logically separate** but intentionally thin in this tree (boundary + export), so they do not get a fifth/sixth product repo.

---

## Bridge areas (not separate projects)

### Encyclopedia (owner TBD)

- **In this repo:** resolve/select hooks under `cluster_review/encyclopedia*.py`, pipeline encyclopedia step, docs that describe the hand-off.  
- **Sibling:** content/tooling in the `encyclopedia` package when installed.  
- **Rule:** ingest must not depend on Wikipedia live calls; encyclopedia is optional after a bag exists.

### Chatbot (Aleena Harold Peter + Anusha)

- **In this repo:** `export/chatbot_export.py` and the export/manifest contract.  
- **Elsewhere:** ClimateInsight / chatbot UI and RAG runtime.  
- **Rule:** corpus JOSS claims a **stable export**, not a chat product.

---

## Shared fabric (all modules)

| Concern | Where |
|---------|--------|
| Paper IDs, path stems | `repositories/_ids.py`, coding style vocabulary |
| Review table as corpus QA | `corpus_review/` |
| Orchestration | `pipeline/` (optional extras per step) |
| Tests | `tests/` with markers where useful (`live_api`, future `gs` / `kg`) |
| Style | [coding_style.md](../coding_style.md) — including **no mocks** |

---

## Suggested install extras (direction)

Aim for optional deps so JOSS “core” stays ingest-focused, e.g.:

- default / `[ingest]` — BagIt, EPMC, review table  
- `[gs]` — Global South scrapers’ extra deps if any  
- `[kg]` or `[cluster]` — sklearn/networkx/yake/streamlit as needed  
- `[encyclopedia]` — sibling encyclopedia  
- `[chatbot]` — only if export needs extras (usually none)

Exact extra names can land in `pyproject.toml` in a follow-up; docs own the *intent* now.

---

## Package layout (target naming)

Today code still lives under mixed paths (`ingestion/`, `repositories/`, `cluster_review/`, …). **Logical** modules map as follows; physical renames are optional later:

| Logical module | Primary paths today |
|----------------|---------------------|
| Ingest + BagIt | `core/`, `ingestion/`, `storage/`, `repositories/europe_pmc.py`, `openalex.py`, `cli*.py` |
| Global South | `repositories/scielo.py`, `redalyc.py`, `conicet.py`, LA uni adapters, `_scraper.py` |
| Phrases + KG | `cluster_review/step2.py`, `step3.py`, `kg.py`, `kg_server.py`, lists |
| Encyclopedia bridge | `cluster_review/encyclopedia*.py` |
| Chatbot bridge | `export/` |
