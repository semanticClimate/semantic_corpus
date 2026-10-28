# Paper–term communities for corpus filtering

**Date:** 2026-10-28 (system date of generation; strategy updated same day)  
**Status:** Design outline for human-in-the-loop filtering  
**UI prototype target:** Streamlit (first iteration)  
**Branch:** `pmr202610`

---

## 1. Purpose

After a query harvest, open literature often mixes **on-topic papers** with **false positives** that share only peripheral vocabulary.

We extract **fast, imperfect terms**, build a **paper–term graph**, detect **communities** (densely co-linked papers and terms), and ask a human to label each community. Labels propagate to member papers (and optionally to terms), refining the review table before encyclopedia / RAG use.

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

## 3. Term extraction strategy (YAKE first)

Community filtering needs **discriminative** terms, not perfect scientific keyphrases. Encyclopedia and dictionary quality need **precise** terms — that work comes **after** curation.

### 3.1 Decision

| Stage | Extractor | Role |
|-------|-----------|------|
| **Prototype / community filtering** | **YAKE** (fast) | Build paper–term graph; expect noise and FP themes |
| **Optional boost** | Query phrases + small curated seed list | Anchor the true topic in the graph |
| **After Keep set exists** | **KBIR** (or slower scientific KE) | Enrich encyclopedia / dictionary on **included** papers only |

**Do not block the prototype on KBIR.** At ~5 minutes per paper it is too slow for iterative community/UI work. Run it later on the much smaller curated set.

### 3.2 Why YAKE is acceptable here

- Speed allows same-day graph and UI iteration.  
- Co-occurrence of imperfect phrases is often enough to separate themes.  
- This workflow **assumes** false-positive communities from scientific discourse (methods boilerplate, shared geography, generic “climate” / “data” / “model” language, statistical jargon).  
- Humans Reject whole themes; they do not need clean keyphrases first.

### 3.3 Known YAKE weaknesses (and mitigations)

| Risk | Mitigation |
|------|------------|
| Generic scientific boilerplate | Stop-ish science lexicon; min length; document-frequency min/max; IDF-weight edges |
| Missed technical multiwords | Boost query terms / seed dictionary into the graph |
| Surface variants (*heatwave* / *heatwaves*) | Light normalize before graph build |
| Noisier encyclopedia if used raw | **Never** feed YAKE-only lists straight into final encyclopedia — re-extract with KBIR (or curated dict) on Keep papers |
| More communities to Reject | Acceptable at ~50 papers; revisit hygiene before scaling to hundreds |

### 3.4 Staging

1. **Now:** YAKE (+ query/seed boost) → communities → Streamlit Keep/Reject.  
2. **Same pilot:** boilerplate filters and optional “similarity to query” hint scores.  
3. **After curation:** KBIR (or equivalent) on **include** papers for encyclopedia / dictionary.  
4. **Optional check:** on 5–10 papers, compare YAKE vs KBIR community themes for sanity — not a gate for v1.

---

## 4. Workflow

```text
Corpus (titles, abstracts, full text if available)
        │
        ▼
① Fast term extraction — YAKE (+ query/seed boost)
   Light normalize; drop boilerplate / extreme df terms
        │
        ▼
② Build paper–term graph (weighted optional)
        │
        ▼
③ Community detection (resolution tuned for a handful of interpretable groups)
        │
        ▼
④ Rank / summarise each community
   - top terms
   - sample titles / abstract snippets
   - optional similarity-to-query score
        │
        ▼
⑤ Human labels each community in the UI
   Keep | Reject | Split / inspect members | Unsure
        │
        ▼
⑥ Propagate labels → review table (include / exclude)
   Optionally demote terms that appear only in Rejected communities
        │
        ▼
⑦ Orphans → individual review queue
        │
        ▼
⑧ Optional: re-run detection on the Keep set if it still looks mixed
        │
        ▼
⑨ Precise term pass on Keep papers — KBIR / scientific KE / curated dictionary
        │
        ▼
⑩ Encyclopedia, export, local LLM
```

### Notes

- Expect **several** communities (multiple false-positive themes), not a single TP/FP split.  
- Scientific discourse **will** create FP groups under YAKE; that is a feature of the review step, not a failure of extraction.  
- Do **not** auto-delete until a human confirms.  
- A second pass on the Keep set is **re-clustering a subset**, not unsupervised recursion until “only TP remain.”  
- Seed with existing review-table decisions when available.  
- KBIR is a **downstream enrichment**, not part of the community-filter critical path.

---

## 5. Inputs and outputs

### Inputs

- Paper list (IDs, titles, abstracts, paths) from the corpus / review table  
- **v1 terms:** YAKE keyphrases per paper (+ optional query/seed terms)  
- **Later terms:** KBIR / dictionary hits on the Keep set for encyclopedia  
- Optional: query string or seed “true topic” papers for ranking  

### Outputs

- Community membership (paper ↔ community_id, term ↔ community_id)  
- Human labels per community + timestamp / curator  
- Updated `review_status` on papers (`include` / `exclude` / `review`)  
- Optional: term denylist or down-weighted dictionary entries  
- Audit trail suitable for citizen-science trust (“why was this excluded?”)  
- After step ⑨: higher-quality term lists for encyclopedia building  

---

## 6. UI outline (Streamlit, v1)

### 6.1 Entry

- Select corpus / review table path  
- Show counts: papers, terms, communities, orphans, already labelled  
- Show term source badge: e.g. `YAKE` (prototype)  
- Actions: **Run / refresh communities**, **Load previous labels**

### 6.2 Community list (main screen)

One card (or table row) per community:

| Element | Content |
|---------|---------|
| Title | `Group {id}` + auto theme from top 3–5 terms |
| Size | *N* papers, *M* terms |
| Top terms | Chip list (expect some noisy YAKE phrases) |
| Samples | 3–5 paper titles (expand for abstract snippet) |
| Hint score | Optional “similarity to query” (advisory only) |
| Decision | **Keep** / **Reject** / **Unsure** |
| Drill-in | **Inspect members** |

### 6.3 Community detail

- Full member paper list with checkboxes (override individual papers)  
- Full member term list (flag “demote term on Reject”)  
- Optional mini graph: papers–terms within this community only  
- Save overrides without changing the whole-community label  

### 6.4 Orphan queue

- Papers (and optionally terms) not in a meaningful community  
- Same include/exclude controls as the HTML review table  
- Batch actions secondary to community labelling  

### 6.5 Summary / export

- Counts after labelling (include / exclude / still review)  
- Export updated review table JSON/CSV  
- Short narrative log: which groups were rejected and top terms (for documentation / PRISMA notes)  
- Reminder / hook: **Run precise term extraction (KBIR) on Keep set** before encyclopedia  

### 6.6 Non-goals for v1

- Multi-user auth and permissions  
- Full-corpus force-directed graph as the primary UI  
- Fully automatic reject without confirmation  
- KBIR (or other slow KE) inside the refresh-communities loop  

---

## 7. Human decision rules (suggested)

| Label | Effect |
|-------|--------|
| **Keep** | Member papers → `include` (unless individually overridden) |
| **Reject** | Member papers → `exclude`; offer to demote community-only terms |
| **Unsure** | Leave papers as `review`; park group for a second curator |
| **Inspect / split** | No bulk write until member-level saves |

Orphans never inherit a community Reject by silence — they stay in the individual queue.

---

## 8. Implementation sketch (later)

| Layer | Suggestion |
|-------|------------|
| Term extraction (v1) | YAKE; optional query/seed injection; boilerplate/df filters |
| Term extraction (post-Keep) | KBIR or scientific KE on `include` papers only |
| Graph + communities | NetworkX or igraph + Leiden/Louvain |
| Ranking | Top terms by weight; optional embedding distance to query |
| Persistence | Sidecar JSON next to review table, then merge into `review_status` |
| UI | Streamlit app under `scripts/` or `apps/community_review/` |
| Next product step | Reuse the same workflow model inside ClimateInsight when stable |

---

## 9. Why Streamlit for v1

- Matches existing #semanticClimate / encyclopedia demos  
- Fast to iterate on cards, tables, and write-back to JSON  
- Enough for workshops and single-curator pilots  

Revisit a shared web UI (e.g. ClimateInsight) once the workflow and data contract are stable.

---

## 10. Success criteria (pilot)

1. Curator can label all communities for a ~50-paper corpus in one sitting.  
2. Rejected communities correspond to inspectable false-positive themes (by curator judgement), including themes driven by scientific boilerplate.  
3. Review table updates are reproducible from saved community labels.  
4. Orphans and Unsure items remain visible — nothing silently dropped.  
5. Community refresh completes in a **short** interactive time (YAKE-scale), not KBIR-scale.  
6. Encyclopedia work uses a **precise** term pass on the Keep set, not raw YAKE alone.

---

*Related: review table workflow docs under `docs/`; keyphrase / encyclopedia tooling in the wider #semanticClimate stack.*
