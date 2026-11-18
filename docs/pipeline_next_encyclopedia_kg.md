# Next steps: `encyclopedia` and `kg`

**Date:** 2026-11-03  
**Status:** `encyclopedia` wired; **`kg` v1 wired** (clusters edges + HTML; wikipedia soft-attach from entries.json)  
**Parent:** [pipeline.md](pipeline.md) · [pipeline_design.md](pipeline_design.md) §5.8–5.9

After `clusters` (and preferably after `clean`), the pipeline should grow two partner steps:

1. **`encyclopedia`** — resolve retained phrases to Wikipedia / Wikidata pages  
2. **`kg`** — assemble a linked knowledge graph, generate edges, and **display** it  

```text
… → clusters → clean ──► encyclopedia
         │          ▲         │
         └────► kg ─┴─────────┘   (kg depends on clusters;
                 │                 encyclopedia soft-attaches when present)
                 └──── FP islands (human confirm) ──► clean
```

---

## 1. `encyclopedia`

**Full step definition:** [pipeline_encyclopedia.md](pipeline_encyclopedia.md)

Resolve retained phrases → Wikipedia / Wikidata; write `encyclopedia/entries.json`.  
Flags: `--encyclopedia-lang`, `--max-entries`. Cap and rank phrases before fetch; statuses `resolved` / `ambiguous` / `missing` / `error`. Does **not** build the multi-edge KG (that is `kg`).

```bash
pipeline --workdir corpora/amoc_insolation_20 \
  --encyclopedia-lang en --max-entries 50 \
  --target encyclopedia
```

---

## 2. `kg` — edges, islands, display

### Goal

Build a **displayable** knowledge graph whose nodes include papers, phrases, and encyclopedia entities, and whose **edges** come from several link generators. Surface weakly connected **islands** as FP hints back into `clean` (human confirm only).

### Planned artifacts

```text
<workdir>/kg/
  graph.json         # nodes + edges (typed)
  islands.json       # components off the main topical core
  kg_summary.json    # counts, link-source stats
  # optional exports for viewers (GraphML, HTML)
```

### Link / edge sources

| Source | Flag token | Edge idea |
|--------|------------|-----------|
| **Clusters (BKG)** | `clusters` | Paper↔phrase (and phrase co-membership) already in the bipartite graph |
| **Wikipedia text links** | `wikipedia` | Outgoing / incoming wikilinks among resolved encyclopedia pages |
| **Wikidata embedding / proximity** | `wikidata` | Related Q-ids via embeddings or structured neighbours (P361, P279, sitelinks, …) |

CLI:

| Flag | Role | Default |
|------|------|---------|
| `--kg-links` | Comma-separated link generators to run | `clusters,wikipedia,wikidata` |
| `--kg-max-island` | Max island size to highlight as FP hints | `20` |
| `--open` | Open `knowledge_graph.html` in the browser | off |

```bash
# After clusters — BKG paper↔term graph + interactive HTML
pipeline kg --workdir corpora/amoc_insolation_20 --kg-links clusters --open

# Include encyclopedia entity nodes when entries.json exists
pipeline kg --workdir corpora/amoc_insolation_20 \
  --kg-links clusters,wikipedia --kg-max-island 20 --open

# Or via full pipeline target
pipeline run --workdir corpora/amoc_insolation_20 \
  --kg-links clusters --target kg
```

Omit a source to skip it, e.g. `--kg-links clusters,wikipedia`.

### Tools (to build)

1. **Edge generators** (library + pipeline actions)  
   - `links_from_clusters(workdir)` → BKG edges  
   - `links_from_wikipedia(entries)` → wikilink edges  
   - `links_from_wikidata(entries, *, embedding=…)` → proximity / embedding edges  

2. **Assemble** — merge nodes/edges, tag `source=` on each edge, write `kg/graph.json`.  

3. **Islands** — connected-component / soft-core analysis → `islands.json` for the clean UI.  

4. **Display**  
   - Streamlit stage “Knowledge graph” (neighbourhood, island panel, “Send to clean”)  
   - Optional static HTML / GraphML export under `kg/` for external tools  

---

## 3. Suggested implementation order

1. Wire `encyclopedia` action: phrase selection + `--max-entries` + MediaWiki fetch → `entries.json`.  
2. `kg` v1: **clusters** edges only + simple viewer (reuse BKG membership).  
3. Add **wikipedia** wikilink edges.  
4. Add **wikidata** proximity / embedding edges (start with structured neighbours; embeddings as a follow-on).  
5. Island detection → clean feedback loop.  
6. Polish Streamlit display (filters by edge source, phrase search, export).

---

## 4. Flags / commands (wired)

- `--encyclopedia-lang`, `--max-entries` — encyclopedia step  
- `--kg-links`, `--kg-max-island`, `--open` — `pipeline kg` / `--target kg`  
- Artifacts: `kg/graph.json`, `kg/islands.json`, `kg/kg_summary.json`, `kg/knowledge_graph.html`

**Tests:**

```bash
pytest tests/test_kg.py tests/test_pipeline.py -k 'encyclopedia or kg'
```

Covers option validation, `--target kg` plan (after `clusters`), stamp recording, and offline KG build + HTML.
