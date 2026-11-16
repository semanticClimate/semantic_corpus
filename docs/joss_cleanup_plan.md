# JOSS cleanup plan — `semantic_corpus` (draft)

**Date:** 2026-11-16 (system date)  
**Status:** draft — lead thinking will change; do not mass-delete until leads agree  
**Primary JOSS target (this repo):** **semantic_corpus** — ingest + BagIt  
**Lead authors on all five papers:** Renu Kumari, Peter Murray-Rust  

This plan separates **what belongs in a clean `semantic_corpus` JOSS package** from material that is trial noise, or that belongs in sibling papers / other repos.

---

## 1. Paper map (working division)

| Paper / theme | Leads (plus Renu & PMR on all) | Likely home | Notes for this cleanup |
|---------------|------------------------------|-------------|-------------------------|
| **semantic_corpus** | Renu Kumari | **this repo** | Ingest mechanisms, BagIt structure, EPMC/OpenAlex-style OA intake, review table as *corpus QA* |
| **Harvesting Global South repos** | Larisa Beni | this repo *adapters* now; maybe split later | non-EN, Redalyc, SciELO, CONICET (+ other LA scrapers) |
| **Phrase extraction & bipartite KG** | Neel Kumar | `cluster_review/` / pipeline KG *or* sibling | figure captions, txt2phrases, lightweight approaches |
| **Encyclopedia** | TBD | sibling `encyclopedia` + hooks here | Wikipedia/Wikidata resolution; keep thin API boundary in this repo |
| **Chatbot** | Aleena Harold Peter + Anusha | ClimateInsight / chatbot repos | export contract / manifest only here |

**Implication:** a JOSS paper on **semantic_corpus** should showcase **ingest + BagIt (+ minimal review/export)**, not ship every AMOC harvest, agrochemical PDF pile, or full KG/encyclopedia demo tree.

---

## 2. Keep in the published `semantic_corpus` tree

### Software (core)

| Path | Why (JOSS / Renu paper) |
|------|-------------------------|
| `semantic_corpus/core/` | Corpus manager, interfaces, exceptions |
| `semantic_corpus/ingestion/` | Ingest paths (pygetpapers dir, local PDF, query output) |
| `semantic_corpus/storage/` | BagIt / document storage |
| `semantic_corpus/repositories/europe_pmc.py` (+ `_ids`, streams, diagnostic) | Primary OA harvest path |
| `semantic_corpus/repositories/openalex.py` | Optional scholarly graph intake (if claimed in paper) |
| `semantic_corpus/corpus_review/` (thin) | Review table as **quality gate on ingest**, not full science product |
| `semantic_corpus/cli.py`, `cli_pygetpapers.py`, `utils.py` | User-facing entry |
| `semantic_corpus/export/` | Thin chatbot **export contract** (hand-off to Aleena/Anusha paper) |
| `tests/` + **small** `tests/fixtures/` / `tests/resources/` | Real files only; no mocks (coding style §0) |
| `scripts/` needed for install/demo (e.g. review viewer, style check) | Document which are “supported” |
| `config/` — **1–2** example YAMLs | e.g. one EPMC pilot; not every topic |
| `pyproject.toml`, `README.md`, `LICENSE`, `.github/` | Packaging / CI |
| `docs/` — **paper-facing only** (see §4) | Install, BagIt layout, ingest tutorial, architecture |

### Keep but mark “also used by sibling papers” (do not delete yet; may move later)

| Path | Sibling paper |
|------|----------------|
| `semantic_corpus/repositories/{scielo,redalyc,conicet,*_colombia,*uba,usp,uchile,unam,kerwa,…}` | Global South harvesting (Larisa) |
| `semantic_corpus/cluster_review/` (phrases, clusters, kg) | Phrase + bipartite KG (Neel) |
| `semantic_corpus/pipeline/` encyclopedia/kg steps | Neel + encyclopedia TBD |
| `semantic_corpus/classification/` | Optional; review-table labelling — decide if in corpus JOSS or later |
| `notebooks/corpus_query_review_colab.ipynb` | Demo; one notebook max for JOSS |
| `apps/cluster_review/` | Neel / UI — not required for ingest JOSS |

---

## 3. Delete or untrack (little/no value for JOSS)

### A. Data dumps (remove from git; optional Zenodo later)

| Path | Approx. | Action |
|------|---------|--------|
| **`corpora/`** entire tree | ~3 GB; ~3100 tracked files | **`git rm -r corpora/`**; gitignore `corpora/` except maybe `corpora/.gitkeep` |
| Especially `corpora/amoc_200/` | ~2.9 GB | Never belongs in a software paper repo |
| Other topic bags (climate_anxiety, monsoon_*, heatwave_*, amoc_*, akalya_project, …) | | Same — trial harvests |
| **`temp/`** | ~2.1 GB | Ensure fully gitignored; delete local scratch freely |
| **`junk/`** | scrap PMC pulls | Delete; gitignore if it returns |
| **`tool_research/`** | loose XML samples | Delete from repo |
| **`agrochemicals/`** | ~106 MB PDFs | Delete from repo (Larisa topic reading ≠ software) |
| **`build/`** | setuptools artefact | Delete + gitignore |
| **`roger/`** | empty | Delete |
| **`results.json/`** | one-off search dump | Delete |

### B. Root / docs trial artefacts

| Path | Action |
|------|--------|
| `apply_climate_anxiety_review.py` | Remove or move to `docs/archive/` — one-off decisions script |
| `rebuild_html_only.py` | Remove or archive |
| `my_first_query.py` | Remove or fold into one tutorial |
| `error.log`, `.DS_Store` | Delete; gitignore |
| `docs/Neel_kumar1.mp4`, large poster JPG | Out of software repo (or release asset) |
| Tracked `__pycache__/` under examples/tests/package | `git rm -r` + ensure gitignore |

### C. Excessive examples / duplicate tutorials

| Path | Action |
|------|--------|
| `examples/01_…` … `examples/11_…` | Keep **2–3** for JOSS (create corpus; search+download EPMC; validate BagIt). Drop or archive the rest |
| `examples/cluster_review/` | Move narrative to Neel paper / keep one pointer README |
| `tutorials/` (repo root) | Merge into `docs/tutorials/`; delete duplicate root tree |
| Second notebook if redundant | Keep one Colab entry point |

---

## 4. Docs: keep vs archive for JOSS

### Keep (semantic_corpus JOSS + shared)

- `docs/overview.md` (trimmed), BagIt / ingest tutorials, `docs/bagit_structure.md` if present  
- `docs/coding_style.md`, `docs/branch_strategy_vs_prs.md` (community, short)  
- `docs/python_source_map.md` (orientation)  
- EPMC resume / pipeline ingest docs that describe **collect → bag**  
- Chatbot **export contract** only (link out to chatbot paper)

### Archive or drop from JOSS default tree (move to `docs/archive/2026/` or wiki)

| Path | Reason |
|------|--------|
| `docs/branches2026_09_29/` | Branch archaeology |
| `docs/sessions/`, `docs/records/`, `docs/summary/` | Meeting/progress logs |
| `docs/demo/`, ocean-heatwaves progress/proposal | Demo narrative → Neel or separate Zenodo |
| `docs/orat_plan.md`, `docs/structure_migration_plan.md`, `docs/phase1_implementation_summary.md`, `docs/development_plan.md` | Internal planning |
| `docs/authors_202611.md` | Useful internally; optional in JOSS tarball |
| Long uniqueness / poster drafts | Cite from paper; don’t ship media |

---

## 5. Suggested ownership of cleanup tasks

| Owner | Cleanup focus |
|-------|----------------|
| **Renu (+ PMR)** | Define JOSS “minimal product”: ingest + BagIt + tests; approve delete list; trim README/examples |
| **Larisa** | Confirm which LA adapters are “paper software” vs experiments; PDFs in `agrochemicals/` out of git |
| **Neel** | Claim or defer `cluster_review/` + KG demos; don’t block corpus JOSS on full phrase stack |
| **Encyclopedia (TBD)** | Keep only import/boundary docs in this repo |
| **Aleena + Anusha** | Own chatbot UI/repos; this repo only stable export schema |

---

## 6. Proposed execution order (when leads say go)

1. **Freeze** JOSS claim list (one paragraph: what the software *is*).  
2. **`git rm -r` data trees:** `corpora/`, `agrochemicals/`, `junk/`, `tool_research/`, `build/`, `roger/`, `results.json/`.  
3. **Tighten `.gitignore`:** `corpora/`, `temp/`, `junk/`, `build/`, `__pycache__/`, media dumps.  
4. **Collapse examples** to ≤3; merge `tutorials/` → `docs/tutorials/`.  
5. **Docs pass:** move archive material under `docs/archive/`; README links only to JOSS paths.  
6. **Tests:** offline suite green; live EPMC only with `SC_LIVE_API=1`; no mocks.  
7. **Optional:** tag `pre-joss-cleanup` before the big `git rm` for archaeology.

### Example commands (do not run until approved)

```bash
git checkout nov2026   # or a fresh joss-cleanup branch
git tag pre-joss-cleanup

git rm -r corpora agrochemicals junk tool_research build roger results.json
git rm -f apply_climate_anxiety_review.py rebuild_html_only.py my_first_query.py error.log
# then edit .gitignore; trim examples/; git rm selected example_*.py
```

---

## 7. Out of scope for this cleanup (explicit)

- Rewriting Neel’s phrase/KG algorithms  
- Splitting Larisa’s adapters into a new repo (can be a *later* paper milestone)  
- Building the chatbot (Aleena/Anusha)  
- Encyclopedia content curation (TBD)  

---

## 8. Decision checklist (leads)

- [ ] Confirm JOSS paper scope = **ingest + BagIt** (± review table as QA)  
- [ ] Approve deleting **all** of `corpora/` from git  
- [ ] Approve deleting `agrochemicals/`, `junk/`, `tool_research/`  
- [ ] Which **N** examples remain (list filenames)  
- [ ] Is `cluster_review/` in corpus JOSS, Neel JOSS, or both with a clear boundary?  
- [ ] Is Global South adapter code cited in corpus JOSS or only Larisa’s paper?  

When these are checked, turn this draft into a tracked issue and execute on a `joss-cleanup` branch.
