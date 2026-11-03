# Step definition: `encyclopedia`

**Date:** 2026-11-03  
**Status:** Wired (`build_encyclopedia` + `pipeline --target encyclopedia`); live MediaWiki tests (no mocks)  
**Pipeline symbol:** `encyclopedia`  
**UI label (legacy):** Step 6 — Encyclopedia KG partner (resolution half; graph assembly is `kg`)  
**Related:** [pipeline.md](pipeline.md) · [pipeline_next_encyclopedia_kg.md](pipeline_next_encyclopedia_kg.md) · [pipeline_design.md](pipeline_design.md) §5.8 · [cluster_filtering_workflow.md](cluster_filtering_workflow.md) §12.9

---

## 1. Purpose

Resolve **retained corpus phrases** to **encyclopedia entities** (Wikipedia pages + Wikidata items) and cache them under `--workdir` for:

- human inspection (Streamlit “Encyclopedia” stage)  
- the downstream **`kg`** step (nodes + Wikipedia/Wikidata edge generators)  
- optional FP signals later (via `kg` islands → `clean`, not auto-delete)

This step does **not** build the multi-source knowledge graph; that is **`kg`**.  
This step does **not** replace BKG cleaning; it prefers phrases that survived `clean`.

---

## 2. Position in the pipeline

```text
phrases → clusters → clean ──► encyclopedia ──► kg
                         │
                         └── (if clean skipped: still runnable after clusters,
                              using cluster/phrase terms — noisier)
```

| | |
|--|--|
| **doit / CLI target** | `--target encyclopedia` |
| **Hard dependency (graph)** | `clusters` |
| **Soft preference** | Use Keep papers + non-demoted terms from `clean` when present |
| **Produces input for** | `kg` |

CLI example:

```bash
# Prefer cluster terms (default when clusters/ exists)
pipeline --workdir corpora/amoc_insolation_20 \
  --encyclopedia-lang en --max-entries 50 --min-score 1.0 \
  --target encyclopedia

# Force current phrase caches under phrases/
pipeline --workdir corpora/amoc_insolation_20 \
# Preferred dedicated CLI (phrases → wiki + disambiguation + HTML):
pipeline encyclopedia --workdir corpora/amoc_insolation_20 \
  --min-paper-count 2 --max-entries 50 --force

# Or via full pipeline target:
pipeline run --always --workdir corpora/amoc_insolation_20 \
  --encyclopedia-from phrases --min-paper-count 2 --max-entries 50 \
  --target encyclopedia
```

---

## 3. Inputs

### 3.1 From earlier steps (under `--workdir`)

| Artifact | Role |
|----------|------|
| `phrases/` (+ `phrases/index.json`) | Phrase strings, `display`, scores, paper membership |
| `clusters/clusters.json` (optional) | Theme membership; ranking by BKG weight |
| `clusters/demoted_terms.json` (if `clean` ran) | Exclude demoted terms |
| `review/review_table.json` (if present) | Exclude `exclude` papers when ranking / attributing |

### 3.2 Flags

| Flag | Type | Default | Meaning |
|------|------|---------|---------|
| `--encyclopedia-lang` | str | `en` | Wikipedia language project (`en`, `de`, …) |
| `--max-entries` | int ≥ 1 | `100` | Maximum phrases to resolve this run |
| `--min-score` | float | `0.0` | Drop phrases/terms below this cluster weight or phrase score |
| `--min-paper-count` | int ≥ 1 | `1` | Minimum `n_papers` when reading `phrases_terms.csv` |
| `--encyclopedia-from` | `auto`\|`clusters`\|`phrases` | `auto` | Phrase pool (`phrases` prefers `phrases_terms.csv`, else caches) |

### 3.3 Phrase selection algorithm

1. **Candidate set**  
   - If clean decisions exist: terms appearing on **Keep** papers, minus demoted terms.  
   - Else: terms from `clusters.json` (member terms), else union of phrase caches.  

2. **Rank** (highest first), using the first available signal:  
   - BKG edge weight sum (phrase↔paper) from clusters graph, else  
   - phrase TF-IDF / YAKE best score × n_papers from phrase index.  

3. **Truncate** to `--max-entries`.  

4. **Normalize key** = lowercase phrase id (same as phrase cache `phrase` field); keep `display` for UI.

---

## 4. Actions (normative)

For each selected phrase, in order:

1. **Cache hit** — if `entries.json` already has a terminal status for this phrase + lang, skip fetch unless force.  
2. **Wikipedia resolve** — MediaWiki API search / exact title for `--encyclopedia-lang`; record best title + pageid + URL.  
3. **Wikidata link** — sitelink or wbsearchentities → `wikidata_id` (`Q…`) when available.  
4. **Status** — one of:  
   - `resolved` — wiki title (+ optional Q-id)  
   - `ambiguous` — multiple candidates; store top-k in `candidates`  
   - `missing` — no acceptable hit  
   - `error` — HTTP / parse failure (retryable)  
5. **Disambiguation** (default on) — for `ambiguous` hits or `*(disambiguation)*` titles, call the sibling [`encyclopedia`](https://github.com/semanticClimate/encyclopedia) resolver (`resolve_disambiguation`) with paper sentences from the corpus. On a clear win, set `status=resolved`, record `disambiguation_history` / `pointer_*`. Close scores stay `ambiguous`.  
6. Append a line to `fetch_log.jsonl`.  
7. Respect rate limits (sleep / Retry-After); never hammer the API.

Idempotent re-runs fill only missing / `error` rows unless `--always` / force.

---

## 5. Outputs

All under `<workdir>/encyclopedia/`:

### 5.1 `entries.json`

```json
{
  "step": "encyclopedia",
  "workdir": "...",
  "params": {
    "lang": "en",
    "max_entries": 50,
    "phrase_source": "clean|clusters|phrases",
    "selected_count": 50
  },
  "entries": [
    {
      "phrase": "atlantic meridional overturning circulation",
      "display": "Atlantic Meridional Overturning Circulation",
      "status": "resolved",
      "wiki_title": "Atlantic meridional overturning circulation",
      "wiki_lang": "en",
      "wiki_pageid": 123456,
      "wiki_url": "https://en.wikipedia.org/wiki/Atlantic_meridional_overturning_circulation",
      "wikidata_id": "Q625632",
      "wikidata_url": "https://www.wikidata.org/wiki/Q625632",
      "candidates": [],
      "fetched_at": "2026-11-03T..."
    }
  ]
}
```

### 5.2 `fetch_log.jsonl`

One JSON object per attempt: `phrase`, `action`, `http_status`, `detail`, `ts`.

### 5.3 Stamp

`pipeline/encyclopedia.stamp` — options + counts + path to `entries.json`; `status: ok` when the action succeeds.

### 5.4 Layout

```text
<workdir>/
  encyclopedia/
    entries.json
    encyclopedia.html              # AmiEncyclopedia wiki-normalized HTML
    fetch_log.jsonl
  pipeline/
    encyclopedia.stamp
```

HTML is built with the sibling [`encyclopedia`](https://github.com/semanticClimate/encyclopedia) package (`AmiEncyclopedia.save_wiki_normalized_html`), mapping `entries.json` → Ami entry dicts. Install with `pip install -e ../encyclopedia` (or clone next to this repo).

---

## 6. Uptodate / skip-if-done

The step is **current** when all hold:

1. `encyclopedia/entries.json` exists.  
2. `encyclopedia/encyclopedia.html` exists (AmiEncyclopedia export).  
3. `params.lang` and `params.max_entries` match the current CLI options.  
4. `params` records the same phrase-source fingerprint (hash of selected phrase ids before fetch).  
5. Stamp exists (and, in real mode, points at that file).

Otherwise remake (or incremental fill of missing phrases).

`pipeline run --always … --target encyclopedia` forces remake.

---

## 7. Failure behaviour

| Situation | Behaviour |
|-----------|-----------|
| No phrases to select | Succeed with empty `entries` list; stamp ok; warn |
| Partial API failures | Keep prior resolved rows; mark failures `error`; exit 0 if any progress, non-zero if zero resolved and all errored |
| Rate limit | Back off; resume later via skip-if-done on remaining |
| Clean not run | Allowed only if dependency graph is relaxed later; today graph requires `clean` first |

---

## 8. Non-goals (this step)

- Building cross-entity edges (→ **`kg`**, `--kg-links`)  
- Display graph / island detection (→ **`kg`** + Streamlit)  
- Auto-removing FP phrases from the corpus  
- Downloading full article HTML dumps (summary / title / Q-id is enough for v1)  
- KBIR or LLM rewriting of encyclopedia text  

---

## 9. Downstream contract for `kg`

`kg` may assume:

- Every node it wants from the encyclopedia side appears in `entries.json` with `phrase` + `status`.  
- Prefer edges only among `status == "resolved"` (and optionally `ambiguous` with a chosen candidate).  
- Wikipedia wikilink and Wikidata proximity generators read `wiki_title` / `wikidata_id`.

---

## 10. Tests (when implementing)

| Level | What |
|-------|------|
| Unit | Phrase selection + rank + `--max-entries` truncate (on-disk fixtures, no network) |
| Live | `resolve_phrase_wikipedia` / `build_encyclopedia` against MediaWiki |
| Live | `pipeline --target encyclopedia` on `corpora/amoc_insolation_20` |

No mocks or injectable fakes — resolve always uses the live API.

---

## 11. Implementation checklist

1. ~~`semantic_corpus/cluster_review/encyclopedia.py` — select, resolve, write.~~  
2. ~~Wire `actions.run_encyclopedia`.~~  
3. ~~`is_step_current("encyclopedia")` checks `entries.json` + params fingerprint.~~  
4. Streamlit stage: table of entries, open wiki/Wikidata links, progress.  
5. Then implement **`kg`** ([pipeline_next_encyclopedia_kg.md](pipeline_next_encyclopedia_kg.md)).

**CLI**

```bash
pipeline --workdir corpora/amoc_insolation_20 \
  --encyclopedia-lang en --max-entries 10 --target encyclopedia

# or
python examples/pipeline/run_encyclopedia.py \
  --workdir corpora/amoc_insolation_20 --max-entries 10
```

**Tests:** `tests/test_encyclopedia.py` (selection fixtures; live MediaWiki resolve/CLI).
