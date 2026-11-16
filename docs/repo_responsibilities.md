# In-repo responsibilities (one repo, logical separation)

**Date:** 2026-11-16  
**Policy:** Do **not** split into separate GitHub projects for each JOSS paper unless leads decide later. Keep themes separable by **package + docs ownership**.

Co-authors on all papers: **Renu Kumari**, **Peter Murray-Rust**.

| Theme | Owner focus | Primary paths in this repo |
|-------|-------------|----------------------------|
| **semantic_corpus** (ingest + BagIt) | Renu Kumari | `ingestion/`, `storage/`, `core/`, EPMC (+ shared CLI), BagIt docs |
| **Global South harvesting** | Larisa Beni | `repositories/` SciELO, Redalyc, CONICET, LA university adapters; non-EN notes |
| **Phrases + bipartite KG** | Neel Kumar | `cluster_review/` (esp. step2–3, kg), lightweight phrase docs |
| **Encyclopedia** | TBD | Hooks: `cluster_review/encyclopedia*.py`, pipeline encyclopedia step; sibling `encyclopedia` package |
| **Chatbot** | Aleena Harold Peter + Anusha | `export/chatbot_export.py` + export contract docs; UI lives in chatbot/ClimateInsight |

Shared: `corpus_review/` (table as corpus QA), `pipeline/` orchestration, `tests/`, coding style.

See also [joss_cleanup_plan.md](joss_cleanup_plan.md).
