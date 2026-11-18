# In-repo responsibilities (one repo, logical separation)

**Date:** 2026-11-16  
**Policy:** Do **not** split into separate GitHub projects for each JOSS theme unless leads later decide. Keep themes separable by **module docs + ownership**.  

**Authoritative module docs:** [modules/README.md](modules/README.md)  
**Package contract:** [`semantic_corpus/MODULE_SPEC.md`](../semantic_corpus/MODULE_SPEC.md)

Co-authors on all papers: **Renu Kumari**, **Peter Murray-Rust**.

| Theme | Owner focus | Module | Module doc | Primary paths |
|-------|-------------|--------|------------|---------------|
| **Corpus ingest + BagIt** | Renu Kumari | `corpus` | [modules/corpus/overview.md](modules/corpus/overview.md) | `core/`, `ingestion/`, `storage/`, `corpus_review/`, CLI |
| **Literature repositories** | Larisa Beni | `repositories` | [modules/repositories/overview.md](modules/repositories/overview.md) | `repositories/` (EPMC, SciELO, Redalyc, CONICET, LA adapters) |
| **Phrases + bipartite KG** | Neel Kumar + Anusha | `phrases_kg` | [modules/phrases_kg/overview.md](modules/phrases_kg/overview.md) | `cluster_review/` step2–3, `kg*` |
| **Encyclopedia** (bridge) | TBD | — | [modules/README.md](modules/README.md) | `encyclopedia*.py` + sibling package |
| **Chatbot** (bridge) | Aleena + Anusha | — | [modules/README.md](modules/README.md) | `export/`; UI elsewhere |

Shared: `pipeline/`, `tests/`, [coding_style.md](coding_style.md), `semantic_corpus.module_meta`.

**JOSS series strategy** (owners, meetings, transcript evidence for community): [joss_series_strategy.md](joss_series_strategy.md).  
Cleanup: [joss_cleanup_plan.md](joss_cleanup_plan.md).
