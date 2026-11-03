# Cluster-review Steps 0–3 — progress

**Date:** 2026-11-01  
**Status:** Steps **0–3 implemented and run end-to-end** on a 50-paper live corpus  
**Next:** Steps 4–6 — BKG cleaning loops (FP papers/terms), orphans/export, optional encyclopedia KG partner to Step 4 (**no Step 7**)  
**Detail design:** [cluster_filtering_workflow.md](cluster_filtering_workflow.md)  
**Orchestration (Make / doit):** [pipeline_make_doit.md](pipeline_make_doit.md)  
**Poster sketch:** [aukget-poster-a0-sketch.jpg](aukget-poster-a0-sketch.jpg)

---

## Summary

| Step | Name | Status | What it does |
|------|------|--------|--------------|
| **0** | Query → download → BAGIT | **Done** | Search Europe PMC (etc.), download XML, create/refresh BAGIT under `corpora/` |
| **1** | Load BAGIT | **Done** | Validate bag, list papers, pin active corpus (workshops can start here) |
| **2** | Phrases | **Done** | Corpus TF-IDF (+ uppercase phrases) on **XML body only**; cache under `phrases/` |
| **3** | BKG + clusters | **Done** | Bipartite paper↔term KG (BKG) + Louvain; read-only under `clusters/` |
| **4** | BKG clean | **Not started** | Weed FP **papers** and FP **terms**; recompute loop → 3 |
| **5** | Orphans + export | **Not started** | Orphan Keep/Remove + curated review snapshot |
| **6** | Encyclopedia KG | **Not started** | Optional partner to 4 — Wikipedia/Wikidata islands → Step 4 |

**Entry rule:** Step 0 **or** Step 1 yields the active corpus; Steps 2–3 are the same either way.

---

## Live worked example (`AMOC AND India`, limit 50)

Corpus root: `corpora/amoc_india_2026/`

| Artifact | Result (2026-11-01) |
|----------|---------------------|
| Papers | **50** (Europe PMC XML) |
| Phrases | **607** unique terms (`method=tfidf`, `n=3`, `top=15`, `text_fields=xml_body`) |
| Clusters | **15** multi-paper clusters |
| Orphans | **6** papers (not actionable until Step 5) |
| Graph | 749 paper↔term edges |

Paths:

```text
corpora/amoc_india_2026/
  data/…                    # BAGIT payload (XML, metadata, …)
  phrases/                  # Step 2 — per-paper JSON + CSV + index.json
  clusters/                 # Step 3 — clusters.json, orphans.json, graph_summary.json
```

Harvest (Step 0 only): `temp/queries/amoc_india_2026/` — not the YAKE/cluster workspace.

### False positives vs query `AMOC AND India`

Step 3 surfaces several **real FPs**, concentrated in a few microbiology / methods clusters rather than spread evenly across all themes. (Louvain `resolution` default `1.0`; lower → fewer, larger clusters.)

#### (a) Papers

**Clear FPs** (wrong domain; query hit incidental):

- Soil / microbes / genes: tea-field nitrifiers, watershed C–N microbes, activated-sludge metagenomics, “viral dark matter”, forest fungi N/P, biochar–microplastics, aquaculture–mangrove N₂O, fertilizer/microbiome orphans  
- Biomedical: injectable dipeptide hydrogels (`PMC9893456`)

**Soft FPs** (climate, but not AMOC–India):

- “Ten new insights…”, Paris Agreement / carbon-neutrality surveys, global fire weather, reforestation temperature, Greenland biodiversity

**Mostly on-topic:** AMOC / North Atlantic / Indian Ocean–monsoon / Tibetan Plateau teleconnection papers.

#### (b) Terms

**Clear FPs:**

- Author-style: `Xu and Wang`, `Chipasa and Medrzycka`, `Hope and Schaefer`, `Allison and Martiny`  
- Orgs / vendors: `Thermo Fisher Scientific`, `World Health Organization`, `Jiaotong University`, `Kyoto Encyclopedia of Genes and Genomes`  
- Methods / lab: `DNA`, `RNA`, `ANOVA`, `KEGG`, `ASVs`, `NMDS`  
- Calendar junk: `May`, `Sep`  
- Discourse slip: `Appendix Table`

**Topical (keep):** `AMOC`, `ISM` / `ISMR`, `Indian Ocean`, `Labrador Sea`, `EASM`, `Tibetan Plateau`, etc.

---

## What each implemented step delivers

### Step 0 — Query → download → BAGIT ✅

- Multi-repo search/download via existing adapters (default Europe PMC).  
- Raw query directory + optional BAGIT create under `corpora/<query-name>/`.  
- Review table initialized (`review` status).  
- **Code:** `semantic_corpus/cluster_review/step0.py`  
- **CLI/example:** `examples/cluster_review/run_steps_0_2.py` (from-step 0), `step0_create_from_query.py`  
- **Tests:** `tests/test_cluster_review_step0.py`

### Step 1 — Load BAGIT ✅

- Load demo or arbitrary BAGIT path; validate layout; paper list + review table.  
- Workshops may skip Step 0.  
- **Code:** `semantic_corpus/cluster_review/step1.py`  
- **CLI/example:** `examples/cluster_review/step1_load_bagit.py`  
- **Tests:** `tests/test_cluster_review_step1.py`

### Step 2 — Phrases ✅

- **Default:** corpus TF-IDF on **XML body only** (no front matter / title / abstract; skips References, Acknowledgments, and similar sections).  
- Document-grounded uppercase phrases (places, acronyms) merged into the top-*k* list.  
- Editable stop lists under `semantic_corpus/cluster_review/lists/` (including `scientific_discourse.txt`).  
- Each phrase JSON entry: `phrase` (lowercase key) + `display` (usual capitalization, e.g. `ISM`, `NegE`) + `score`.  
- YAKE remains available as `method="yake"`.  
- **Code:** `semantic_corpus/cluster_review/step2.py`, `lists_loader.py`, `lists/*.txt`  
- **CLI/example:** `run_steps_0_2.py` (to-step 2), `step2_extract_yake.py`  
- **Tests:** `tests/test_cluster_review_step2.py`, `tests/test_cluster_review_lists.py`  
- **UI:** Streamlit Step 2 in `apps/cluster_review/app.py`

### Step 3 — Clusters (read-only) ✅

- Bipartite graph from phrase cache; Louvain communities (greedy modularity fallback).  
- Writes `clusters.json` (themes use `display` forms), `orphans.json`, `graph_summary.json`.  
- UI shows cluster cards; Keep/Remove is **Step 4** (not yet).  
- **Code:** `semantic_corpus/cluster_review/step3.py`  
- **CLI/example:** `examples/cluster_review/step3_build_clusters.py`  
- **Tests:** `tests/test_cluster_review_step3.py`  
- **UI:** Streamlit Step 3 in `apps/cluster_review/app.py`

---

## How to reproduce Steps 0–3

```bash
# Steps 0–2 (limit 50, force fresh phrases)
./venv/bin/python examples/cluster_review/run_steps_0_2.py \
  --limit 50 --force-yake --clear-phrases --info

# Step 3
./venv/bin/python examples/cluster_review/step3_build_clusters.py \
  --corpus-dir corpora/amoc_india_2026

# Or Streamlit
./venv/bin/streamlit run apps/cluster_review/app.py
```

---

## Update BAGIT with additional files (any later stage)

Not a numbered curation step. After an active corpus exists (Step 1+), fetch **missing PDFs** into `data/documents/pdf/` without re-running the query.

- Skips valid PDFs already on disk (`%PDF` + size ≥ 10 KB); rejects HTML/error stubs.  
- Europe PMC sources: OA S3 → FTP zip → OA PDF URLs (same as Step 0).  
- Updates bag manifests and refreshes `has_pdf` on an existing review table when present.

```bash
./venv/bin/python examples/cluster_review/update_corpus_files.py \
  --corpus-dir corpora/amoc_india_2026 --formats pdf
```

**Code:** `semantic_corpus/cluster_review/update_corpus.py` (`update_bagit_formats`)  
**UI:** Streamlit sidebar + Step 1 panel — **Update corpus files (PDF)**

---

## Not in Steps 0–3 (planned 4–6; no Step 7)

- **Step 4:** BKG cleaning loop — FP papers + FP terms; recompute clusters  
- **Step 5:** Orphan queue + curated export  
- **Step 6:** Encyclopedia / Wikidata KG as **optional partner to Step 4** (FP islands)  
- Standalone “Step 7 remove FPs” — **removed**; cleaning is the graph feedback loops  

See workflow diagram in [cluster_filtering_workflow.md §3](cluster_filtering_workflow.md#3-planned-end-to-end-product-with-kg-cleaning-loops).

---

## Deliverables checklist

| Deliverable | Present |
|-------------|---------|
| Library modules `step0`–`step3` | Yes |
| Editable phrase stop lists | Yes |
| Unit tests for steps 0–3 + lists | Yes |
| CLI / example scripts | Yes |
| Streamlit shell (Steps 0–3) | Yes |
| Live 50-paper corpus + phrases + clusters | Yes (`amoc_india_2026`) |
| Poster layout sketch | Yes (`docs/aukget-poster-a0-sketch.jpg`) |
| Update BAGIT with PDFs (any later stage) | Yes (`update_corpus.py`) |
| Steps 4–5 BKG clean + orphans/export | No |
| Step 6 encyclopedia KG (optional partner to 4) | No |
| Step 7 (standalone FP removal) | Removed — use cleaning loops |
