# Prompt archive — corpus design (standalone core)

**Date:** 2026-11-18  
**Purpose:** Preserve the human prompt that drove corpus design work, for JOSS evidence that development follows communal strategy (see [docs/joss_series_strategy.md](../docs/joss_series_strategy.md) §4).  
**Derived design:** [docs/modules/corpus/design.md](../docs/modules/corpus/design.md)  
**Continuation:** [prompt_2026-11-18_corpus_design_cont.md](prompt_2026-11-18_corpus_design_cont.md)

---

## Prompt (verbatim)

NOTE: In all discussions please include prompts so we can show JOSS that you are developing code in response to our strategy.

Design for corpus (the standalone core) . This is a lightweight filestore-as-database (possibly with a NoSQL or similar  index if it gets large). corpus consists of:
* BAGIT filestore of non-semantic literature (documents, diagrams, tables but not databases). This is incrementat perhaps over the cours eof a research project.
* It should roughly support CRUD. 
* Ingested material has no schema and may need to be guessed at input. Initially input will be underb human control (no agents - this may develop.
* ingested material should be semanticised into sesction and paragraphs (for  text), figures and capitions, tables and captions (using HTML builtins where possible. Semantic operations may be described in declarative manner, so that non-coders can specify XPaths or regex outside the code.
* ideally the ingest code shild be indepenent of the material ingested , being controlled declaratively
* the extent of some inputs will be precisely defined (*e.g. IPCC WGs and SRs). Others will be sample queries from large services (e.g. EPMC or Redalyc). 
* all inputs may be terminated by humans or user limits. Reruns may be defined to ingest the next chunk, or N new query results
*. Individual entries are unlikely to change over time so Update will be uncommon, but might be Rerun when software changes (e.g. on input)
[more coming ... stay quiet]
