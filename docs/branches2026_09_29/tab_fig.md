# Branch: `tab_fig`

**Remote tip:** `origin/tab_fig` @ `0fae19a` (*added citizen climate*)  
**Local:** currently checked out; tracks `origin/tab_fig`  
**vs `origin/main`:** ahead **14**, behind **30**  
**Verdict:** **Primary merge** for demo/docs/PRISMA/review UX (after rebasing onto updated `main`).

---

## Why it matters

Carries the **ocean_heatwaves_2026** end-to-end demo narrative, review-table viewer improvements, PRISMA helpers, multi-repository adapters (OpenAlex/SciELO/Redalyc), chatbot export fixes, and the **citizen science climate knowledge prospectus**.

---

## Useful unmerged content

### Docs (keep)

- `docs/demo/*` — proposal, runbook, progress, ClimateInsight adapter plan  
- `docs/outreach/citizen_science_climate_knowledge_prospectus.md` (**unique vs `renu`**)  
- `docs/orat_plan.md`, `docs/prisma_flow.md`, `docs/structure_migration_plan.md`  
- Dated records/summaries under `docs/records/`, `docs/summary/` (Jul 2026 ocean heatwaves)  
- Tutorials: HTML review table, new-member quickstart  

### Code (keep)

- `semantic_corpus/corpus_review/` — download completeness, PRISMA flow/diagram, HTML viewer, review viewer server, interactive review  
- `semantic_corpus/repositories/` — OpenAlex, SciELO, Redalyc, `_scraper`, `_ids` (coordinate with larisaBeni versions)  
- `semantic_corpus/export/chatbot_export.py` — citation_label fix for author dicts  
- `semantic_corpus/transformation/xml_to_html.py`  
- Scripts: `build_example_corpus.py`, `review_viewer.py`, `interactive_review.py`, …  
- Tests: `test_prisma_flow.py`, `test_html_review_viewer.py`, `test_repository_adapters*.py`, …  

### Fixtures (keep selectively)

- `tests/fixtures/ocean_heatwaves_2026/` — curated review + manifest + included XML (good development fixture)  
- Prefer **not** merging entire `temp/queries/` or full BAGIT trees if fixtures already cover the demo  

### Config

- `config/ocean_heatwaves_2026.yaml`, `climate_anxiety_2026.yaml`, `openalex_*`, `redalyc_*`, `scielo_*`

---

## Overlap / conflicts

- Shares ancestry with `renu` and parts of `vrinda`.  
- Repository adapters and review viewer also exist on `larisaBeni`/`conicet` — merge larisa first, then rebase `tab_fig` and resolve duplicates toward one API.  
- **30 commits behind** `main` (akalya corpus deletions on main) — expect noisy conflicts in `corpora/`.

---

## Suggested merge approach

```text
main ← larisaBeni
main ← rebase/merge tab_fig
  → keep docs/demo + docs/outreach
  → keep tests/fixtures/ocean_heatwaves_2026 (trim PDFs if needed)
  → drop accidental temp/ harvest bulk if present in diff
```

Then cherry-pick unique `renu` tutorial files (see [renu.md](renu.md)).
