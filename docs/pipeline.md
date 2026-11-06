# Pipeline CLI (`pipeline`)

**Date:** 2026-11-03  
**Status:** CLI + doit orchestration live; **`collect` / `corpus` / `phrases` / `clusters` / `encyclopedia` / `kg` are real**; `pdfs` / `clean` / `--source` still placeholders or partial.  
**Examples:** [pipeline_examples.md](pipeline_examples.md) · **Tutorial:** [tutorials/kg_from_query.md](tutorials/kg_from_query.md)  
**Next:** [pipeline_encyclopedia.md](pipeline_encyclopedia.md) · [pipeline_next_encyclopedia_kg.md](pipeline_next_encyclopedia_kg.md)  
**Related:** [pipeline_design.md](pipeline_design.md) · [pipeline_make_doit.md](pipeline_make_doit.md) · [cluster_filtering_workflow.md](cluster_filtering_workflow.md)

Install:

```bash
pip install -e '.[cluster_review,test]'   # doit, sklearn, networkx, streamlit, …
```

Console script: **`pipeline`** (also `python -m semantic_corpus.pipeline`).

---

## 1. Mental model

Context is **`--workdir`**, not the shell’s current directory (unlike classic Make looking for a `Makefile` in cwd).

| Idea | Flag / step | Meaning |
|------|-------------|---------|
| Corpus root | `--workdir DIR` | Where the BAGIT corpus lives (and where later artifacts are written) |
| Live search | `--query "…"` | Europe PMC (etc.) search; **requires** query flags |
| Local files | `--source PATH` | Alternate start (placeholder ingest for now) |
| Goal | `--target STEP` | Ensure this step; run missing dependencies only |
| Remake | `run --always` | Ignore skip-if-done; remake the target chain |

```bash
pipeline --workdir corpora/amoc_insolation_20 \
  --query "amoc AND insolation" --limit 20 \
  --phrase-method tfidf --cluster-resolution 0.8 \
  --target clusters
```

**Infer start mode**

| Flags given | Start | What runs toward `--target clusters` |
|-------------|-------|--------------------------------------|
| `--query "…"` | `collect` | `collect` → `corpus` → `phrases` → `clusters` (remotes) |
| `--source PATH` | `collect` | same plan; static documents via `--source` |
| neither | `existing` | `corpus` → `phrases` → `clusters` |

`--query` and `--source` are mutually exclusive.

---

## 2. Dependency graph

```text
--query (EPMC/remotes) ─┐
                        ├──► collect ──► corpus (+indexes) ──► phrases ──► clusters [--kg→KG₁]
--source (static docs) ─┘        │                                      │
(neither) ──────────────────► corpus …                                  ▼
                                     └──► pdfs                     clean
                                                                        │
                                                                        ▼
                                                              encyclopedia [--kg→KG₂]
# design: two display KGs via --kg flag (not a step); clean after clusters
# detail: docs/pipeline_kg_mappers.md
```

| Step | Design role | Implementation today |
|------|-------------|----------------------|
| `collect` | Collect documents | `--query`: real EPMC/remotes; `--source`: static (placeholder) |
| `corpus` | Bag gate **+** packet indexes | Real load + `packets/manifest.json` |
| `phrases` | Traverse indexed texts → terms | Real (`step2`) |
| `pdfs` | Fill PDFs (parallel) | Placeholder |
| `clusters` | Map (BKG); optional **KG₁** (`--kg`) | Real (`step3` + optional `build_kg`) |
| `clean` | Curate graph FPs before annotate | Placeholder; depends on `clusters` |
| `encyclopedia` | Annotate retained terms; optional **KG₂** (`--kg`) | Real; depends on `clean` |

**Display KG is not a step** — use `--kg` / `--no-kg` on `clusters` (plain) or `encyclopedia` (Wikipedia-annotated; may add Wikidata). `pipeline kg` rebuilds the HTML helper.

**`corpus` (not `bagit` as a step name).** BagIt remains the **on-disk format** (`bagit.txt`). **`collect`** is the single intake step: remotes (`--query`, `--repository`, …) or static documents (`--source`). Packaging into the bag is part of producing that corpus.

Inspect:

```bash
pipeline list
pipeline graph --from collect
pipeline graph --from existing
```

---

## 3. `--workdir` layout (where results go)

For `--workdir corpora/amoc_insolation_20`:

```text
corpora/amoc_insolation_20/          # --workdir (BAGIT corpus root)
  bagit.txt
  data/documents/xml/ …
  data/metadata/
  phrases/                           # from --target phrases|clusters
    index.json
    …
  clusters/                          # from --target clusters
    clusters.json
    orphans.json
    graph_summary.json
  pipeline/                          # pipeline stamps
    collect.stamp
    corpus.stamp
    phrases.stamp
    clusters.stamp
  # NOTE: doit DB is NOT under the bag (bagit.make_bag would move it into data/)

temp/pipeline_doit/<workdir>_<hash>/doit.db   # per-corpus doit dependency DB
temp/queries/amoc_insolation_20/              # harvest dir (name = workdir basename)
  PMC….xml
  search_results.json
  review/
```

The harvest directory is **`temp/queries/<workdir.name>/`**, not inside the bag. The bag is only under **`--workdir`**.

---

## 4. Skip-if-done (why a re-run can take seconds)

Like Make/doit: if stamps and key artifacts are already current, steps are **skipped**.

| Output | Meaning |
|--------|---------|
| `.  collect` | Ran this time |
| `-- collect` | Skipped (up to date) |

A second `pipeline … --target clusters` on the same `--workdir` will often finish in a few seconds and **not** re-query Europe PMC. That is intentional.

**Force remake**

```bash
pipeline run --always --workdir corpora/amoc_insolation_20 \
  --query "amoc AND insolation" --limit 20 --target clusters
```

Or forget selected stamps:

```bash
pipeline forget --workdir corpora/amoc_insolation_20 --target phrases
pipeline --workdir corpora/amoc_insolation_20 --query "amoc AND insolation" --limit 20 --target clusters
```

Note: even with `--always`, the downloader may still reuse XMLs already present under `temp/queries/<name>/` if the repository layer skips existing files.

---

## 5. Flags by step

### Query (required on the search path)

| Flag | Role | Default |
|------|------|---------|
| `--query` / `-q` | Search string | *(required for search)* |
| `--limit` / `-n` | Max hits | `20` |
| `--repository` | Adapter | `europe_pmc` |

### Phrases

| Flag | Role | Default |
|------|------|---------|
| `--phrase-method` | `tfidf` \| `yake` | `tfidf` |
| `--phrase-n` | n-gram size | `3` |
| `--phrase-top` | Top-k per paper | `15` |

### Clusters

| Flag | Role | Default |
|------|------|---------|
| `--cluster-algorithm` | Community detection | `louvain` |
| `--cluster-resolution` | Louvain resolution | `1.0` |

### Encyclopedia / kg

| Flag | Role | Default |
|------|------|---------|
| `--encyclopedia-lang` | Wikipedia language | `en` |
| `--max-entries` | Cap phrases resolved for encyclopedia | `100` |
| `--kg-links` | Edge generators: `clusters`, `wikipedia`, `wikidata` | `clusters` |
| `--kg-max-island` | Island size hint threshold for clean feedback | `20` |
| `--kg-min-paper-count` | Min `n_papers` (phrases_terms) for a term node | `2` |
| `--kg-max-terms` | Cap term nodes after ranking by `n_papers` | `40` |
| `--open` / `--no-open` | Open `knowledge_graph.html` after kg | on |

```bash
# After clusters — interactive KG HTML (defaults filter + open browser)
pipeline kg --workdir corpora/amoc_insolation_20
```

Detail: [pipeline_encyclopedia.md](pipeline_encyclopedia.md) · [pipeline_next_encyclopedia_kg.md](pipeline_next_encyclopedia_kg.md).

---

## 6. Examples

Numbered recipes: **[pipeline_examples.md](pipeline_examples.md)**.

### 1. AMOC — 30 papers → clusters + plain KG

```bash
pipeline --workdir corpora/amoc_30 \
  --query "AMOC" --limit 30 \
  --target clusters --kg
```

**Plan:** `collect → corpus → phrases → clusters` (+ **KG₁**).  
Detail / remake / next steps: [pipeline_examples.md §1](pipeline_examples.md#1-amoc--30-papers--clusters--plain-kg).

### Older fixture (limit 20, insolation)

```bash
pipeline --workdir corpora/amoc_insolation_20 \
  --query "amoc AND insolation" --limit 20 \
  --phrase-method tfidf --phrase-n 3 --phrase-top 15 \
  --cluster-resolution 0.8 \
  --target clusters
```

**Live pytest** (uses `run --always`):

```bash
pytest tests/test_pipeline.py::test_example_amoc_insolation_limit_20_to_clusters -s
```

Needs network + `doit` + `scikit-learn` + `networkx`. Marked `live_api` / `network` / `slow`.  
Unit tests use `PIPELINE_PLACEHOLDER=1` (stamps only).

---

## 7. Other useful commands

```bash
pipeline status --workdir corpora/amoc_insolation_20 --query "amoc AND insolation" --target clusters
pipeline --workdir corpora/amoc_india_2026 --target clusters          # existing bag
pipeline --workdir corpora/amoc_insolation_20 --query "…" --target pdfs
pipeline forget --workdir corpora/amoc_insolation_20 --target clusters
```

**doit name clash:** public step `clean` maps to task basename `clean_fp` (doit reserves `clean`). Use `--target clean`.

**Placeholder env:** `PIPELINE_PLACEHOLDER=1` forces stamp-only actions (used by unit tests).

---

## 8. Implementation map

| Piece | Path |
|-------|------|
| CLI | `semantic_corpus/pipeline/cli.py` |
| Options / env | `semantic_corpus/pipeline/config.py` |
| Step graph | `semantic_corpus/pipeline/steps.py` |
| Real actions | `semantic_corpus/pipeline/actions.py` |
| doit tasks | `semantic_corpus/pipeline/dodo.py` |
| Stamps | `semantic_corpus/pipeline/placeholders.py` |
| Tests | `tests/test_pipeline.py` |

Streamlit should call the same tasks via `DoitMain` + `ModuleTaskLoader` (not `doit.run()`, which calls `sys.exit`). See [pipeline_make_doit.md](pipeline_make_doit.md).

---

## 9. Encyclopedia + display KGs

- Examples: [pipeline_examples.md](pipeline_examples.md)  
- **`encyclopedia`:** [pipeline_encyclopedia.md](pipeline_encyclopedia.md)  
- Design: [pipeline_kg_mappers.md](pipeline_kg_mappers.md)

```bash
# Plain KG after clusters (KG₁)
pipeline --workdir corpora/amoc_30 --query "AMOC" --limit 30 --target clusters --kg

# After clean: annotated KG (KG₂)
pipeline --workdir corpora/amoc_30 --target encyclopedia --kg
```
