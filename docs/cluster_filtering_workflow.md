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
Step 0: Query → download → (optional) BAGIT create
   or
Step 1: Load existing BAGIT
                    │
                    ▼
         YAKE phrases  →  Bipartite graph  →  Clusters
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

**Explicit non-delivery in this document:** no Streamlit script, no YAKE runner, no graph code yet — plan and stepped UI outline only.

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

### 5.1 Query → corpus (UI Step 0) or load BAGIT (UI Step 1)

- **Step 0:** Form/YAML: one or more repositories, query, limit 50, dates, formats xml (± pdf). Search + download via adapters; raw query dir + review table; **option to create BAGIT** under `corpora/`.  
- **Step 1:** Load an existing BAGIT (demo ~50-paper `ocean_heatwaves_2026` or user path). Workshops may start here and skip Step 0.

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

## 8. UI build plan — one app, stepped delivery

**Principle:** Ship **one** Streamlit application from day one (`apps/cluster_review/app.py` or `scripts/cluster_review_app.py`). Each step unlocks the next stage in the **same** sidebar/navigation shell. Do not build separate throwaway UIs.

### 8.1 Persistent shell (all steps)

Present from Step 0 onward:

| UI chrome | Role |
|-----------|------|
| Title | Cluster review — semantic_corpus |
| Sidebar: stage list | **Query / BAGIT** → **Load corpus** → Phrases → Clusters → Orphans → Summary |
| Sidebar: entry mode | **Create from query** (Step 0) **or** **Load existing BAGIT** (Step 1) |
| Sidebar: status counts | Papers / phrases ready? / clusters / orphans / include·exclude |
| Main panel | Content for the **active** stage only |
| Footer | Elapsed timers + corpus path / review table path |

Disabled stages show as locked until prerequisites are met (e.g. Phrases locked until a corpus is active; Clusters locked until phrases exist).

**Entry rule:** the user picks **either** Step 0 **or** Step 1 to obtain an active BAGIT corpus; Steps 2+ are identical either way.

### 8.2 Steps

| Step | Name | What the user does |
|------|------|--------------------|
| **0** | **Query → raw / BAGIT corpus** | Search one or more repositories with a query; download; optionally create a **BAGIT** corpus |
| **1** | **Load existing BAGIT** | Open an existing BAGIT corpus (e.g. demo `ocean_heatwaves_2026`) and browse papers |
| **2** | **Phrases (YAKE)** | Extract / cache YAKE phrases for the active corpus |
| **3** | **Clusters (view)** | Build bipartite clusters; inspect themes (read-only) |
| **4** | **Remove clusters** | Iteratively Keep / Remove / Inspect / Unsure; Save review table |
| **5** | **Orphans** | Keep / Remove orphan papers |
| **6** | **Summary + export** | Counts, removal log, download curated review table |

#### Step 0 — Search repositories and create corpus (query path)

- App shell runs; **Query / create** stage active.  
- Choose repository(ies) (e.g. Europe PMC; later multi-select as adapters allow).  
- Enter query, limit (default 50), date bounds, formats (xml ± pdf).  
- **Search** → show hit preview; **Download** into a working query dir (raw corpus).  
- Option: **Create BAGIT corpus** from the download (name + output under `corpora/`).  
- Initialize / refresh review table (statuses `review`).  
- **Done when:** curator has a new BAGIT (or at least a raw query dir ready to bag) from a live query, usable as the active corpus for Steps 2+.

#### Step 1 — Load an existing BAGIT corpus

- **Load corpus** stage: pick path or demo preset (~50-paper `ocean_heatwaves_2026`).  
- Validate BAGIT layout; load paper list + review table.  
- Show **Corpus** table (paper id, title, status).  
- **Done when:** curator can browse the loaded BAGIT with no YAKE/graph yet.  
- Workshops may **skip Step 0** and start here.

#### Step 2 — Phrases (YAKE) inside the same app

- **Phrases** stage: **Extract YAKE** (title+abstract); cache to disk beside the corpus.  
- Progress bar + per-paper timing; **Use cached phrases** if present.  
- Main panel: phrases for a selected paper; corpus-level phrase count.  
- **Done when:** active corpus has cached YAKE phrases without leaving the app.

#### Step 3 — Build clusters (read-only view)

- **Clusters** stage: **Build / refresh clusters** from cached phrases (bipartite graph + Leiden/Louvain).  
- Cluster cards (theme, size, top terms, sample titles) — **view only**.  
- Orphans listed but not actionable yet.  
- **Done when:** curator sees a stable partition and can spot likely FP themes.

#### Step 4 — Iterative cluster removal

- On each card: **Keep** / **Remove cluster** / **Unsure** / **Inspect**.  
- Inspect: member list with per-paper override.  
- Provisional labels in session; **Save** writes review table.  
- Optional **Recompute clusters** on remaining Keep set.  
- **Done when:** FP clusters can be removed and include/exclude persisted.

#### Step 5 — Orphan queue (same app)

- **Orphans** stage: Keep / Remove individuals or multi-select.  
- Orphans remain visible after cluster removals (no silent drop).  
- **Done when:** orphans can be cleared or parked without a second tool.

#### Step 6 — Summary + export

- Counts, log of removed cluster themes, download JSON/CSV.  
- Note: encyclopedia / KBIR later — not in this app.  
- **Done when:** session ends with an exported curated review table.

### 8.3 Backend modules behind the UI (build alongside steps)

| Step | Library work (no second UI) |
|------|-----------------------------|
| 0 | Multi-repo search + download; BAGIT create from query output; review table init |
| 1 | BAGIT / review-table loader (demo + arbitrary path) |
| 2 | `yake` batch + phrase cache I/O |
| 3 | Bipartite graph + cluster + orphan detection |
| 4–5 | Label model + merge into `review_status` |
| 6 | Export helpers |

### 8.4 What not to do

- Do not create a new Streamlit app per step.  
- Do not add KBIR to any step of this UI.  
- Do not force every user through Step 0 — **Load BAGIT (Step 1)** must work alone for demos.  
- Do not treat raw query-dir-only as the long-term store when the user asked for BAGIT — offer explicit **Create BAGIT**.

### 8.5 Suggested coding order vs workshop value

| After completing | Demo you can give |
|------------------|-------------------|
| Step 0 | “Search EPMC (or more repos), download, create BAGIT” |
| Step 1 | “Open the existing 50-paper ocean heatwaves BAGIT” |
| Step 2 | “YAKE phrases in ~2–5 minutes” |
| Step 3 | “Candidate FP themes as clusters” |
| Step 4–5 | Full curation loop (clusters + orphans) |
| Step 6 | Take-home review table |

---

## 9. Implementation sketch (supporting code)

Ordered library deliverables aligned with §8 — application UI is the Streamlit shell above:

1. Query → download → **BAGIT create** (Step 0) using existing repository + corpus managers.  
2. BAGIT loader for demo + path pickers (Step 1).  
3. YAKE batch helper → `phrases/*.json` beside corpus (Step 2).  
4. Graph + cluster module → `clusters.json` (+ orphans) (Step 3).  
5. Wire Steps 4–6 in the same Streamlit app (remove, orphans, export).  
6. Short tutorial: create-or-load, then filter `ocean_heatwaves_2026`.

Layout: `apps/cluster_review/` or `scripts/cluster_review_app.py` + `semantic_corpus/clustering/`.

Dependencies: `yake`, `streamlit`, `networkx` (and/or `igraph` + Leiden).

---

## 10. Success criteria (pilot)

1. User can **create** a BAGIT corpus from a query (Step 0) **or** **load** an existing BAGIT (Step 1), including the ~50-paper demo.  
2. YAKE + first cluster view ready in a few minutes once a corpus is active (cached thereafter).  
3. User can **remove clusters** and **clear orphans** iteratively; review table updates on Save.  
4. No silent drops; Unsure/orphans remain visible.  
5. No KBIR (or other multi-minute-per-paper KE) in the filter loop.  
6. One Streamlit app covers Steps 0–6; Step 0 and Step 1 are alternative entry points.

---

## 11. Out of scope for v1 filter UI

- KBIR / `txt2phrases` transformer extraction inside the loop  
- Multi-user auth  
- Full-corpus force graph as primary UI  
- Automatic remove without confirmation  
- Encyclopedia generation (follows Keep set in a later phase)

---

*Supersedes `docs/community_filtering_workflow.md` (renamed: community → cluster). Related: review-table docs; `docs/download_epmc_pdfs.md` for PDF harvest limits.*
