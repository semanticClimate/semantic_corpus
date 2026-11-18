# Branch: `vrinda`

**Remote tip:** `origin/vrinda` @ `2df0c01` (*Add climate anxiety phrase outputs and encyclopedia*)  
**vs `origin/main`:** ahead **23**, behind **30**  
**Verdict:** **Selective content merge** — curated climate-anxiety workflow + encyclopedia artefacts; avoid bulk BAGIT/XML dump.

---

## Why it matters

Best example of the citizen/demo workflow on a finished topic:

- Reviewed climate anxiety corpus (include / exclude / follow-up)  
- Analysis notes: classification, filtering criteria, extracted terms, provenance  
- Keyphrase CSVs + encyclopedia HTML  
- Tutorials for review-table → encyclopedia  

---

## Useful unmerged content

### Keep (docs / analysis)

- `corpora/climate_anxiety_2026/vrinda_project/README.md`
- `…/analysis/*.md`, `…/provenance/provenance.md`
- `…/first_100_term_encyclopedia_climate_anxiety.html`
- `…/keyphrases.json` and a **sample** of `keyphrases/*.csv` (or compress externally)
- `docs/tutorials/generation_of_review_table.md` (and moves under `docs/tutorials/`)
- Multi-batch review workflow guidance commits
- Helper scripts: `apply_climate_anxiety_review.py`, `rebuild_html_only.py` (if still used)

### Keep (code already overlapping tab_fig)

Review viewer / interactive review / SciELO–Redalyc–OpenAlex — prefer the version landed from `larisaBeni` + `tab_fig`; only pull vrinda-specific fixes if missing.

### Skip or externalise

- Full nested `corpora/climate_anxiety_2026/data/data/documents/**` HTML/XML/PDF trees  
- Entire `temp/queries/climate_anxiety_2026/*.xml` harvest (hundreds of MB-class churn)  

If the full corpus must be preserved, prefer a **release asset** or data repo, not perpetual git history on `main`.

---

## Suggested merge approach

1. Copy/curate a slim `docs/examples/climate_anxiety_2026/` or `tests/fixtures/climate_anxiety_2026/` with review JSON + encyclopedia HTML + keyphrases summary.  
2. Merge tutorial markdown into `docs/tutorials/`.  
3. Leave bulky bags out of `main`.
