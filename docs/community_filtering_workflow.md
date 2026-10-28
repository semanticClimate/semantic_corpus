# Paper–term communities for corpus filtering

**Date:** 2026-10-28 (system date of generation)  
**Status:** Design outline for human-in-the-loop filtering  
**UI prototype target:** Streamlit (first iteration)

---

## 1. Purpose

After a query harvest, open literature often mixes **on-topic papers** with **false positives** that share only peripheral vocabulary.

We build a **paper–term graph**, detect **communities** (densely co-linked papers and terms), and ask a human to label each community. Labels propagate to member papers (and optionally to terms), refining the review table before encyclopedia / RAG use.

All **include / exclude decisions remain human**. Automation proposes structure and rankings only.

---

## 2. Terminology

| Term | Meaning |
|------|---------|
| **Community** | Algorithmic densely connected subgroup (Louvain / Leiden, etc.) |
| **Group** / **theme** | Same object in the UI (friendlier wording) |
| **Orphan** | Paper or term weakly linked or in a trivial component — review individually |
| **Propagate** | Apply a community-level Keep/Reject decision to its member papers |

Use **community** in code and methods docs; prefer **group** or **theme** on screen.

---

## 3. Workflow

```text
Corpus + keyphrases / dictionary hits
        │
        ▼
① Build paper–term graph (weighted optional)
        │
        ▼
② Community detection (resolution tuned for a handful of interpretable groups)
        │
        ▼
③ Rank / summarise each community
   - top terms
   - sample titles / abstract snippets
   - optional similarity-to-query score
        │
        ▼
④ Human labels each community in the UI
   Keep | Reject | Split / inspect members | Unsure
        │
        ▼
⑤ Propagate labels → review table (include / exclude)
   Optionally demote terms that appear only in Rejected communities
        │
        ▼
⑥ Orphans → individual review queue
        │
        ▼
⑦ Optional: re-run detection on the Keep set if it still looks mixed
        │
        ▼
⑧ Continue pipeline (encyclopedia, export, local LLM)
```

### Notes

- Expect **several** communities (multiple false-positive themes), not a single TP/FP split.
- Do **not** auto-delete until a human confirms.
- A second pass on the Keep set is **re-clustering a subset**, not unsupervised recursion until “only TP remain.”
- Seed the process with existing review-table decisions when available.

---

## 4. Inputs and outputs

### Inputs

- Paper list (IDs, titles, abstracts, paths) from the corpus / review table  
- Terms / keyphrases per paper (encyclopedia, `txt2phrases`, dictionary annotation, …)  
- Optional: query string or seed “true topic” papers for ranking  

### Outputs

- Community membership (paper ↔ community_id, term ↔ community_id)  
- Human labels per community + timestamp / curator  
- Updated `review_status` on papers (`include` / `exclude` / `review`)  
- Optional: term denylist or down-weighted dictionary entries  
- Audit trail suitable for citizen-science trust (“why was this excluded?”)

---

## 5. UI outline (Streamlit, v1)

### 5.1 Entry

- Select corpus / review table path  
- Show counts: papers, terms, communities, orphans, already labelled  
- Actions: **Run / refresh communities**, **Load previous labels**

### 5.2 Community list (main screen)

One card (or table row) per community:

| Element | Content |
|---------|---------|
| Title | `Group {id}` + auto theme from top 3–5 terms |
| Size | *N* papers, *M* terms |
| Top terms | Chip list |
| Samples | 3–5 paper titles (expand for abstract snippet) |
| Hint score | Optional “similarity to query” (advisory only) |
| Decision | **Keep** / **Reject** / **Unsure** |
| Drill-in | **Inspect members** |

### 5.3 Community detail

- Full member paper list with checkboxes (override individual papers)  
- Full member term list (flag “demote term on Reject”)  
- Optional mini graph: papers–terms within this community only  
- Save overrides without changing the whole-community label  

### 5.4 Orphan queue

- Papers (and optionally terms) not in a meaningful community  
- Same include/exclude controls as the HTML review table  
- Batch actions secondary to community labelling  

### 5.5 Summary / export

- Counts after labelling (include / exclude / still review)  
- Export updated review table JSON/CSV  
- Short narrative log: which groups were rejected and top terms (for documentation / PRISMA notes)

### 5.6 Non-goals for v1

- Multi-user auth and permissions  
- Full-corpus force-directed graph as the primary UI  
- Fully automatic reject without confirmation  

---

## 6. Human decision rules (suggested)

| Label | Effect |
|-------|--------|
| **Keep** | Member papers → `include` (unless individually overridden) |
| **Reject** | Member papers → `exclude`; offer to demote community-only terms |
| **Unsure** | Leave papers as `review`; park group for a second curator |
| **Inspect / split** | No bulk write until member-level saves |

Orphans never inherit a community Reject by silence — they stay in the individual queue.

---

## 7. Implementation sketch (later)

| Layer | Suggestion |
|-------|------------|
| Graph + communities | NetworkX or igraph + Leiden/Louvain |
| Ranking | Top terms by weight; optional embedding distance to query |
| Persistence | Sidecar JSON next to review table, then merge into `review_status` |
| UI | Streamlit app under `scripts/` or `apps/community_review/` |
| Next product step | Reuse the same workflow model inside ClimateInsight when stable |

---

## 8. Why Streamlit for v1

- Matches existing #semanticClimate / encyclopedia demos  
- Fast to iterate on cards, tables, and write-back to JSON  
- Enough for workshops and single-curator pilots  

Revisit a shared web UI (e.g. ClimateInsight) once the workflow and data contract are stable.

---

## 9. Success criteria (pilot)

1. Curator can label all communities for a ~50-paper corpus in one sitting.  
2. Rejected communities correspond to inspectable false-positive themes (by curator judgement).  
3. Review table updates are reproducible from saved community labels.  
4. Orphans and Unsure items remain visible — nothing silently dropped.

---

*Related: review table workflow docs under `docs/`; keyphrase / encyclopedia tooling in the wider #semanticClimate stack.*
