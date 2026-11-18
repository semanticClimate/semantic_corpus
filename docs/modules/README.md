# Logical modules — one repository (strong default)

**Date:** 2026-11-16 (system date)  
**Decision:** Keep **one** GitHub project (`semanticClimate/semantic_corpus`). Do **not** create a new repo per JOSS theme unless leads later agree APIs are stable and owners can release independently.  
**Co-authors on all papers:** Renu Kumari, Peter Murray-Rust  
**Package contract:** [`semantic_corpus/MODULE_SPEC.md`](../../semantic_corpus/MODULE_SPEC.md) · template: `semantic_corpus/module_template/`

Separation is by **named functionality + ownership + docs**, not by remotes. Each first-class module is a **subpackage** of `semantic_corpus` with the same layout (`module.yaml`, `README.md`, `__init__.py`).

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
**JOSS series strategy** (five papers, owners, weekly meetings, using `discussions/` transcripts for community evidence): [joss_series_strategy.md](../joss_series_strategy.md).

---

## The three extension modules (this folder)

| # | Document | Package | Focus owner | JOSS role |
|---|----------|---------|-------------|-----------|
| 1 | [corpus/overview.md](corpus/overview.md) | `semantic_corpus.corpus` | Renu Kumari | **Primary** software paper for this repo: ingest + BagIt |
| 2 | [repositories/overview.md](repositories/overview.md) | `semantic_corpus.repositories` | Larisa Beni | Repository adapters (EPMC, SciELO, Redalyc, CONICET, …); non-EN |
| 3 | [phrases_kg/overview.md](phrases_kg/overview.md) | `semantic_corpus.phrases_kg` | Neel Kumar + Anusha | Phrase extraction, bipartite clusters/KG, lightweight methods |

**Encyclopedia** and **chatbot** stay **logically separate** bridges (boundary + export), so they do not get a fourth/fifth product repo. They may adopt the same `module.yaml` layout later.

Discover at runtime:

```python
from semantic_corpus.module_meta import list_modules
for meta in list_modules():
    print(meta["name"], meta["title"], meta["owner"])
```

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
| Tests | `tests/` with markers where useful (`live_api`, future `repositories` / `kg`) |
| Style | [coding_style.md](../coding_style.md) — including **no mocks** |
| Module metadata | `semantic_corpus/<name>/module.yaml` via `module_meta` |

---

## Suggested install extras (direction)

Aim for optional deps so JOSS “core” stays ingest-focused, e.g.:

- default / `[ingest]` — BagIt, EPMC, review table  
- `[repositories]` — Global South scrapers’ extra deps if any  
- `[kg]` or `[cluster]` — sklearn/networkx/yake/streamlit as needed  
- `[encyclopedia]` — sibling encyclopedia  
- `[chatbot]` — only if export needs extras (usually none)

Exact extra names can land in `pyproject.toml` in a follow-up; docs own the *intent* now.

---

## Package layout (target naming)

Today code still lives under mixed paths (`ingestion/`, `repositories/`, `cluster_review/`, …). **Logical** modules map as follows; physical moves are optional later—the module package is the stable face:

| Logical module | Package face | Primary paths today |
|----------------|--------------|---------------------|
| Corpus ingest + BagIt | `semantic_corpus.corpus` | `core/`, `ingestion/`, `storage/`, `corpus_review/`, `cli*.py` |
| Literature repositories | `semantic_corpus.repositories` | `repositories/` (EPMC, OpenAlex, SciELO, Redalyc, CONICET, LA adapters) |
| Phrases + KG | `semantic_corpus.phrases_kg` | `cluster_review/step2.py`, `step3.py`, `kg.py`, `kg_server.py`, lists |
| Encyclopedia bridge | *(later)* | `cluster_review/encyclopedia*.py` |
| Chatbot bridge | *(later)* | `export/` |
