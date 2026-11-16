# In-repo responsibilities (one repo, logical separation)

**Date:** 2026-11-16  
**Policy:** Do **not** split into separate GitHub projects for each JOSS theme unless leads later decide. Keep themes separable by **module docs + ownership**.  

**Authoritative module docs:** [modules/README.md](modules/README.md)

Co-authors on all papers: **Renu Kumari**, **Peter Murray-Rust**.

| Theme | Owner focus | Module doc | Primary paths |
|-------|-------------|------------|---------------|
| **Ingest + BagIt** | Renu Kumari | [modules/ingest_bagit.md](modules/ingest_bagit.md) | `ingestion/`, `storage/`, `core/`, EPMC/OpenAlex, CLI |
| **Global South harvesting** | Larisa Beni | [modules/global_south.md](modules/global_south.md) | SciELO, Redalyc, CONICET, LA adapters |
| **Phrases + bipartite KG** | Neel Kumar | [modules/phrases_kg.md](modules/phrases_kg.md) | `cluster_review/` step2–3, `kg*` |
| **Encyclopedia** (bridge) | TBD | [modules/README.md](modules/README.md) | `encyclopedia*.py` + sibling package |
| **Chatbot** (bridge) | Aleena + Anusha | [modules/README.md](modules/README.md) | `export/`; UI elsewhere |

Shared: `corpus_review/` (QA), `pipeline/`, `tests/`, [coding_style.md](coding_style.md).

Cleanup: [joss_cleanup_plan.md](joss_cleanup_plan.md).
