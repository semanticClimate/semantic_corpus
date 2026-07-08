# ORAT Subproject — Architecture, Workflow, and Reuse Plan

**Date:** 2026-07-08 (system date)  
**Status:** Proposed — not implemented  
**Repository:** `semantic_corpus` (subproject ORAT)

---

## Executive summary

ORAT is a new subproject to retrieve open literature, build a corpus, analyse it, and develop a domain vocabulary and encyclopedia. It will draw on sibling repos (`../pygetpapers`, `../encyclopedia`, `../amilib`) where appropriate.

**Scoping decision (2026-07-08):**

- **Phase 1:** Europe PMC only — develop framework and test end-to-end.
- **Phase 2:** Vocabulary and encyclopedia from the reviewed Europe PMC corpus.
- **Phase 3:** Add Redalyc and SciELO after the framework is proven.
- **Deferred:** OpenAlex (not used yet).

---

## Goals

1. Build a reproducible corpus pipeline for ORAT topics.
2. Ingest metadata and full text from open repositories.
3. Normalize records into a common schema and package as a BAGIT corpus.
4. Support human review of paper relevance and quality.
5. Create a curated **vocabulary** and **encyclopedia** (concepts, definitions, aliases, corpus evidence).
6. Analyse the corpus (coverage, trends, concept prevalence).

---

## Phased plan

### Phase 0 — Scoping (Europe PMC only)

Define ORAT inclusion criteria, query strings, languages, years, and success metrics before any large harvest.

| Deliverable | Approach |
|-------------|----------|
| Query spec | YAML config (copy `config/climate_anxiety_2026.yaml` pattern) |
| Pilot size | Small cap (e.g. 25–50 papers) |
| Source | `repository: europe_pmc` only |
| Formats | `xml` + `pdf` |
| Review criteria | What counts as in-scope for ORAT vocabulary/encyclopedia |

**Defer until later phases:** OpenAlex, Redalyc, SciELO, cross-source deduplication.

### Phase 1 — Framework and test (Europe PMC)

Build the ORAT skeleton end-to-end on one source, with tests and team review workflow.

```
config/orat_pilot.yaml
    ↓
search + download (Europe PMC)
    ↓
temp/queries/orat_pilot/
    ├── search_results.json
    ├── query_run.json
    ├── PMC*.xml / PMC*.pdf
    └── review/review_table.{json,csv,html}
    ↓
ingest → corpora/orat_pilot/   (BAGIT)
    ↓
team review (review_viewer.py serve)
    ↓
vocabulary seed → encyclopedia (Phase 2)
```

**Test gates before expanding sources:**

- Query returns relevant papers (manual review of pilot table).
- Downloads succeed (XML + PDF rates logged).
- Ingest produces valid BAGIT corpus.
- Review UI loads papers correctly.
- Save round-trip works (JSON ← HTML edits).

### Phase 2 — Vocabulary and encyclopedia (Europe PMC corpus)

Build ORAT knowledge assets from the **reviewed** Europe PMC corpus before adding new sources.

1. Extract candidate terms from included papers (KeyBERT / phase1 wordlist).
2. Curate wordlist (precision over recall; see IPCC encyclopedia strategy).
3. Build encyclopedia entries with Wikipedia enrichment.
4. Link terms back to corpus evidence (paper IDs, snippets).

### Phase 3 — Redalyc and SciELO

Extend harvest to Latin American sources; introduce cross-source concerns.

**New work at this stage:**

- Cross-source dedup (DOI / title+year merge).
- Source-aware metadata normalization (scrape vs API records).
- Multi-query orchestration (one ORAT run, multiple repos).
- Bias reporting (source composition in final corpus).

**Still deferred:** OpenAlex.

---

## High-level architecture

| Layer | Role |
|-------|------|
| **Config** | Query definitions, limits, date ranges, language filters (`config/orat_*.yaml`) |
| **Acquisition** | Europe PMC fetcher (later: Redalyc, SciELO) |
| **Normalization** | Shared `PaperRecord` schema; source fields in `extras` |
| **Identity and dedup** | Phase 3 only: DOI → PMCID/PMID → title+year+author |
| **Fulltext** | PDF and HTML/XML download with provenance and checksums |
| **Corpus packaging** | BAGIT layout, manifests, metadata tables |
| **Review** | JSON source of truth; HTML for human editing; local server for paper reading |
| **Analysis** | Stats, term extraction, coverage dashboards |
| **Knowledge** | Vocabulary (terms, synonyms) + encyclopedia (concepts, relations, evidence) |

### Proposed folder layout

```
config/
  orat_pilot.yaml

temp/queries/orat_pilot/
  search_results.json
  query_run.json
  PMC*.xml, PMC*.pdf
  review/
    review_table.{json,csv,html,md,css}

corpora/orat_pilot/
  bag-info.txt
  data/
    metadata/
    documents/{xml,pdf,html}/
    analysis/
    provenance/

vocabulary/          # when Phase 2 starts — location TBD under orat or corpora/
encyclopedia/
```

### Data models (target)

**PaperRecord:** `canonical_id`, `source_ids`, bibliographic fields, `abstract`, `subjects`, `access`, `document_paths`, `provenance`.

**VocabularyTerm:** `term_id`, `preferred_label`, `aliases`, `language`, `status`, `evidence_refs`.

**EncyclopediaConcept:** `concept_id`, `label`, `definition`, `aliases`, `relations`, `linked_terms`, `evidence`, `editorial_status`.

---

## End-to-end workflow

1. **Scoping** — ORAT research questions, inclusion/exclusion, Europe PMC query strings.
2. **Pilot harvest** — capped pull; validate relevance and metadata completeness.
3. **Normalization** — common schema (single source in Phase 1; merge in Phase 3).
4. **Fulltext resolution** — download or link; record access constraints.
5. **Corpus QA gate** — duplicate rate, missing fulltext, language/source distribution.
6. **Production harvest** — full query with pagination/resume (after pilot sign-off).
7. **Human review** — `review_table.html` via `review_viewer.py serve`.
8. **Vocabulary build** — semi-automatic extraction + curation.
9. **Encyclopedia build** — concept entries with corpus evidence.
10. **Analysis and reporting** — trends, exports, team-facing tables.
11. **Maintenance** — scheduled refreshes; API drift checks.

---

## Reusable code inventory

### `semantic_corpus` — primary stack (Phase 1)

| Area | Path | Use for ORAT |
|------|------|--------------|
| Europe PMC adapter | `semantic_corpus/repositories/europe_pmc.py` | Harvest |
| Repository API | `semantic_corpus/core/repository_interface.py`, `repository_factory.py` | Pluggable repos (Phase 3) |
| ID helpers | `semantic_corpus/repositories/_ids.py` | Stable paper IDs |
| Workflow | `semantic_corpus/corpus_review/workflow.py` | Search → download → review → ingest |
| Query runs | `semantic_corpus/corpus_review/query_run.py` | YAML + `query_run.json` |
| Ingest | `semantic_corpus/ingestion/query_output_ingester.py`, `pygetpapers_ingester.py` | Flat or pygetpapers layout → corpus |
| Corpus | `semantic_corpus/core/corpus_manager.py`, `storage/bagit_manager.py` | BAGIT packaging |
| Metadata | `semantic_corpus/tools/metadata_processor.py` (+ extractor, validator) | Normalization |
| Review | `semantic_corpus/corpus_review/review_table.py`, `review_viewer_server.py` | Team UI |
| Review schema | `semantic_corpus/corpus_review/review_schema.py`, `constants.py` | include/review/exclude |
| Transform | `semantic_corpus/transformation/xml_to_html.py` | PMC XML → HTML for reading |
| Export | `semantic_corpus/export/chatbot_export.py` | Downstream manifest |
| CLI / scripts | `semantic_corpus/cli.py`, `scripts/build_review_table.py`, `scripts/review_viewer.py` | Operations |
| Examples | `examples/11_aqi_india_workflow.py`, `config/climate_anxiety_2026.yaml` | Templates |
| Reference corpus | `corpora/climate_anxiety_2026/` | 50-paper Europe PMC example |

**Deferred adapters (Phase 3):** `repositories/redalyc.py`, `repositories/scielo.py`, configs `redalyc_climate_change.yaml`, `scielo_climate_change.yaml`.

**Not used:** `repositories/openalex.py`, `config/openalex_climate_anxiety.yaml`.

### `../pygetpapers` — optional deeper harvest

| Path | Notes |
|------|--------|
| `pygetpapers/repositories/europe_pmc/europe_pmc.py` | Fuller Europe PMC implementation (~800 lines) |
| `pygetpapers/repositories/redalyc/`, `scielo/` | Phase 3 if semantic_corpus adapters insufficient |
| `pygetpapers/core/metadata_extractor.py` | HTML metadata for scrapers |
| `pygetpapers/core/abstract_repository.py` | Config-driven repo framework |

**Decision:** Use semantic_corpus adapters first; delegate to pygetpapers or ingest pygetpapers output if needed.

### `../encyclopedia` — vocabulary and encyclopedia (Phase 2)

| Path | Use |
|------|-----|
| `encyclopedia/ipcc/phase1_wordlist.py` | Aggregate keyword CSVs → raw wordlist |
| `encyclopedia/utils/encyclopedia_builder.py` | Terms → dictionary → Wikipedia → encyclopedia |
| `encyclopedia/clustering/clusterer.py` | Concept grouping |
| `encyclopedia/utils/knowledge_graph/` | Wikidata/Wikipedia graph (later) |
| `scripts/create_wordlist_editor_html.py` | Human wordlist curation |
| `docs/IPCC_AR6_ENCYCLOPEDIA_STRATEGY.md` | Process: precision over recall, curation gates |

### `../amilib` — dictionary and text mining

| Path | Use |
|------|-----|
| `amilib/ami_dict.py` | `AmiDictionary` from words/CSV |
| `amilib/ami_encyclopedia.py` | Encyclopedia management, Wikidata normalization |
| `amilib/wikimedia.py` | Wikipedia lookup |
| `amilib/acronym_extractor.py` | Acronym ↔ full-term |
| `amilib/corpus_module/corpus.py` | KeyBERT + TF-IDF term discovery |

---

## Gaps — new work for ORAT

| Gap | When |
|-----|------|
| ORAT-specific Europe PMC query strings and inclusion rules | Phase 0 |
| `config/orat_pilot.yaml` and corpus naming | Phase 1 |
| ORAT-specific review columns or relevance scoring (if needed) | Phase 1 |
| Cross-source deduplication | Phase 3 |
| Multi-source federated harvest | Phase 3 |
| PDF → HTML in semantic_corpus (if required beyond xml_to_html) | As needed |
| Classification module (optional encyclopedia_category columns exist in review UI) | Phase 2+ |

---

## Draft pilot config (not created yet)

```yaml
# config/orat_pilot.yaml
query_name: orat_pilot
query_string: <ORAT Europe PMC query TBD in scoping>
repository: europe_pmc
limit: 25
start_date: "2020-01-01"
end_date: "2026-12-31"
formats:
  - xml
  - pdf
corpus_name: orat_pilot
output_subdir: orat_pilot

success_criteria:
  min_search_results: 10
  min_downloads: 5
```

### Commands (after config exists)

```bash
./venv/bin/python scripts/build_review_table.py \
  --query-dir temp/queries/orat_pilot

./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/orat_pilot/review/review_table.json \
  --query-dir temp/queries/orat_pilot
# → http://127.0.0.1:8765/review_table.html
```

---

## Scoping session — open questions

Before implementation:

1. **ORAT topic definition** — what Europe PMC query string(s)?
2. **Inclusion criteria** — language, document type, geography?
3. **Pilot size** — 25 or 50 papers?
4. **Vocabulary scope** — single encyclopedia or split (cf. IPCC three-encyclopedia model in `../encyclopedia/docs/IPCC_AR6_ENCYCLOPEDIA_STRATEGY.md`)?

---

## Related documentation

| Doc | Purpose |
|-----|---------|
| [aqi_india_corpus_workflow.md](aqi_india_corpus_workflow.md) | Query → ingest → review stages |
| [summary/2026-07-06_review_workflow.md](summary/2026-07-06_review_workflow.md) | HTML review table workflow |
| [tutorials/new_member_review_quickstart.md](tutorials/new_member_review_quickstart.md) | Review UI onboarding |
| [build_review_table.md](build_review_table.md) | Build script reference |
| `../encyclopedia/docs/IPCC_AR6_ENCYCLOPEDIA_STRATEGY.md` | Vocabulary/encyclopedia process |
| `../encyclopedia/docs/semantic_corpus_proposal.md` | Long-term cross-repo vision |

---

## Governance

- Reproducibility: every run tied to config + `query_run.json`.
- Provenance: retain `search_results.json` and download logs.
- Review checkpoints: query adequacy, ingest QA, vocabulary adjudication, encyclopedia sign-off.
- Versioning: corpus snapshot, vocabulary version, encyclopedia version (aligned with encyclopedia repo practices).
