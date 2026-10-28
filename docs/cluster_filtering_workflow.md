# Paper–term clusters for corpus filtering

**Date:** 2026-10-28 (system date; renamed community → cluster; full pipeline plan)  
**Status:** Design / estimate only — **no application code in this commit**  
**UI:** Streamlit (planned)  
**Terms:** **YAKE only** for the filter loop (not KBIR)  
**Branch:** `pmr202610`

---

## 1. Purpose

Build an interactive path from **query → corpus → YAKE phrases → bipartite paper–term graph → clusters**, then let a curator **iteratively remove false-positive clusters (including orphans)** until the retained set is fit for encyclopedia / local LLM work.

All include/exclude decisions remain **human**. The system proposes clusters and ranks; it does not auto-delete.

---

## 2. Terminology

| Term | Meaning |
|------|---------|
| **Cluster** | Densely co-linked subgroup of papers and terms (Louvain / Leiden, etc.) |
| **Theme** | Optional UI label for a cluster (from top terms) |
| **Orphan** | Paper (or term) in a trivial / singleton component — review or remove individually |
| **Remove cluster** | Curator rejects that cluster; member papers marked `exclude` (unless overridden) |
| **Propagate** | Apply a cluster-level Keep/Remove decision to member papers |

Former docs used “community”; **cluster** is the preferred term everywhere in this design.

---

## 3. Planned end-to-end product (not built yet)

One Streamlit app (plus thin library helpers) covering:

```text
Query  →  Corpus  →  YAKE phrases  →  Bipartite graph  →  Clusters
                                                              │
                    ┌─────────────────────────────────────────┘
                    ▼
         Iterative UI: inspect / remove clusters + orphans
                    │
                    ▼
         Updated review table (include / exclude)
                    │
                    ▼
         (Later, out of scope for v1 filter) encyclopedia / KBIR on Keep set
```

**Explicit non-delivery in this document:** no Streamlit script, no YAKE runner, no graph code yet — plan and time estimates only.

---

## 4. Example corpus for users (~50 papers)

**Default demo corpus:** `ocean_heatwaves_2026` (or `climate_anxiety_2026` as fallback).

| Property | Intent |
|----------|--------|
| Size | ~50 papers (query harvest scale already used in demos) |
| Source | Europe PMC open full text where available |
| Bundled for users | Pre-built query dir / fixtures under `tests/fixtures/ocean_heatwaves_2026/` or `temp/queries/…` so the UI can start **without** a live harvest |
| Live path | Optional: run a YAML query (limit 50) then continue into YAKE → clusters |

Workshop mode should default to the **pre-built 50-paper bundle** so elapsed time is dominated by YAKE + human review, not download flakiness.

---

## 5. Pipeline stages (design)

### 5.1 Query → corpus

- Config YAML: repository, query string, limit 50, formats xml (± pdf).  
- Search + download via `semantic_corpus` Europe PMC (and adapters as available).  
- Produce flat query dir + review table (all `review` initially).  
- **Demo shortcut:** load existing 50-paper corpus; skip live download.

### 5.2 Phrases (YAKE)

- Input: title + abstract (and full text if present; abstract-only is OK for speed).  
- YAKE per paper (`yake` package — not `txt2phrases` KBIR).  
- Optional: inject query n-grams / small seed list into each paper’s term set.  
- Hygiene: lowercase, light normalize, drop science-boilerplate stop list, df min/max.  
- Output: per-paper phrase list (JSON/CSV) used only for clustering.

KBIR remains **out of this loop** (optional later on Keep papers for encyclopedia).

### 5.3 Bipartite filter

- Build bipartite graph: paper ↔ term edges (weights optional: YAKE score / tf-idf).  
- Cluster detection (Leiden/Louvain on an appropriate projection or bipartite method).  
- Emit: cluster id, member papers, member terms, orphan papers/terms.  
- Expect **multiple** FP clusters from scientific discourse — not a single TP/FP split.

### 5.4 Iterative human removal (Streamlit)

Loop until the curator stops:

1. Show remaining clusters (size, top terms, sample titles).  
2. Curator **Remove** / **Keep** / **Inspect members** / **Unsure**.  
3. Show **orphan** queue; allow remove/keep per paper.  
4. On Remove: mark papers `exclude`; optionally demote cluster-only terms.  
5. Optionally **recompute clusters** on the remaining Keep set.  
6. Save review table + audit log; offer export.

---

## 6. Streamlit UI outline (planned)

### Screen A — Start

- Choose: **Demo corpus (50 papers)** / path to corpus / optional “run query (limit 50)”.  
- Show query text used for the demo.  
- Buttons: **Load corpus**, **Extract YAKE phrases**, **Build clusters**.  
- Progress + elapsed timers per stage.

### Screen B — Cluster board (main loop)

For each cluster card:

| Element | Content |
|---------|---------|
| Theme | Auto from top 3–5 YAKE terms |
| Size | *N* papers, *M* terms |
| Samples | Titles (+ abstract expand) |
| Actions | **Keep** · **Remove cluster** · **Inspect** · **Unsure** |

Global: remaining paper count, **Recompute clusters**, **Save**, **Finish**.

### Screen C — Cluster inspect

- Member papers with per-paper override (keep one paper while removing rest).  
- Member terms; option “demote these terms if cluster removed”.

### Screen D — Orphans

- List orphan papers (and optionally orphan terms).  
- **Remove** / **Keep** individually or small multi-select.  
- Orphans never disappear silently when a large cluster is removed.

### Screen E — Summary

- Include / exclude / still review counts.  
- Log of removed cluster themes.  
- Download updated `review_table.json` / CSV.  
- Note: precise KE (e.g. KBIR) is a **separate later step** on Keep only.

---

## 7. Estimated elapsed time

Assumptions: laptop/M1-class CPU, demo **pre-built 50-paper** corpus, YAKE on title+abstract (not full PDF OCR), Streamlit local, one curator familiar with the topic.

### 7.1 Machine time (approximate)

| Stage | Estimate (50 papers) | Notes |
|-------|----------------------|--------|
| Load pre-built corpus + review table | **&lt; 5 s** | Disk / JSON |
| Live query + download (optional, not demo default) | **5–20 min** | Network, XML; PDF flaky (see EPMC PDF note) |
| YAKE on title+abstract | **1–3 min** | Roughly 1–4 s/paper; full text may push **5–15 min** |
| Build bipartite graph + cluster | **&lt; 10–30 s** | NetworkX/igraph scale is tiny at n=50 |
| Streamlit recompute after a removal | **&lt; 5–15 s** | If phrases cached |
| **Machine total (demo path)** | **~2–5 min** before human review | Phrases dominate |

If YAKE is run on full text for all 50: budget **~10–20 min** machine time once, then cache phrases on disk.

### 7.2 Human time (approximate)

| Activity | Estimate |
|----------|----------|
| First pass: scan ~5–15 clusters, remove obvious FP themes | **15–30 min** |
| Orphan pass | **5–15 min** |
| Optional second clustering + cleanup | **10–20 min** |
| **Human total** | **~30–60 min** for a careful first curation |

### 7.3 End-to-end workshop slot

| Mode | Wall clock |
|------|------------|
| Demo corpus + YAKE + one curation pass | **~45–75 min** |
| Including live harvest of 50 papers | **~1–2 h** (network-dependent) |
| Contrast: KBIR on 50 papers | **~4 h+** machine alone — why it stays out of v1 |

---

## 8. Implementation plan (when coding starts)

Ordered deliverables — **not started**:

1. YAKE batch helper → `phrases/*.json` beside corpus.  
2. Graph + cluster module → `clusters.json` (+ orphans).  
3. Streamlit app: load demo 50, run/cached YAKE, show clusters, iterative remove, orphans, save review table.  
4. Wire optional live query (limit 50) behind an advanced toggle.  
5. Docs + short tutorial using `ocean_heatwaves_2026`.

Suggested layout later: `apps/cluster_review/` or `scripts/cluster_review_app.py` + `semantic_corpus/clustering/`.

Dependencies (planned): `yake`, `streamlit`, `networkx` (and/or `igraph` + Leiden).

---

## 9. Success criteria (pilot)

1. User can open the app on the **50-paper** example without running a live query.  
2. YAKE + first cluster view ready in a few minutes (cached thereafter).  
3. User can **remove clusters** and **clear orphans** iteratively; review table updates on Save.  
4. No silent drops; Unsure/orphans remain visible.  
5. No KBIR (or other multi-minute-per-paper KE) in the filter loop.

---

## 10. Out of scope for v1 filter UI

- KBIR / `txt2phrases` transformer extraction inside the loop  
- Multi-user auth  
- Full-corpus force graph as primary UI  
- Automatic remove without confirmation  
- Encyclopedia generation (follows Keep set in a later phase)

---

*Supersedes `docs/community_filtering_workflow.md` (renamed: community → cluster). Related: review-table docs; `docs/download_epmc_pdfs.md` for PDF harvest limits.*
