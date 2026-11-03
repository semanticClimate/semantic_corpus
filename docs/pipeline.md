# Pipeline CLI (`pipeline`)

**Date:** 2026-11-03  
**Status:** CLI + doit orchestration live; **`query` / `corpus` / `phrases` / `clusters` / `encyclopedia` are real**; `pdfs` / `clean` / `kg` / `--source` still placeholders or partial.  
**Next:** [pipeline_encyclopedia.md](pipeline_encyclopedia.md) (step definition) · [pipeline_next_encyclopedia_kg.md](pipeline_next_encyclopedia_kg.md)  
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
| `--query "…"` | `query` | `query` → `corpus` → `phrases` → `clusters` |
| `--source PATH` | `documents` | `documents` → `corpus` → `phrases` → `clusters` |
| neither | `existing` | `corpus` → `phrases` → `clusters` |

`--query` and `--source` are mutually exclusive.

---

## 2. Dependency graph

```text
--query  ──► query  ──┐
                      ├──► corpus ──┬──► phrases ──► clusters ──► clean ──► encyclopedia ──► kg
--source ─► documents ┘             └──► pdfs
(neither) ──────────────► corpus …
```

| Step | Role | Implementation today |
|------|------|----------------------|
| `query` | Search + download + **package BAGIT at `--workdir`** | Real (`cluster_review.step0`) |
| `documents` | Ingest `--source` into corpus | Placeholder |
| `corpus` | Ensure bag under `--workdir` (gate for later steps) | Real load if bag exists; also stamped by `query` |
| `phrases` | Keyphrases → `phrases/` | Real (`step2`, TF-IDF/YAKE) |
| `pdfs` | Fill PDFs into the bag | Placeholder (API exists: `update_bagit_formats`) |
| `clusters` | BKG + Louvain → `clusters/` | Real (`step3`) |
| `clean` | FP paper/term cleaning | Placeholder |
| `encyclopedia` | Wiki / Wikidata pages | Placeholder |
| `kg` | Linked graph + islands | Placeholder |

**`corpus` (not `bagit` as a step name).** BagIt remains the **on-disk format** (`bagit.txt`). The pipeline step is named `corpus` because `query` / `--source` must put material somewhere; packaging is part of producing that corpus, not a separate product idea.

Inspect:

```bash
pipeline list
pipeline graph --from query
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
  pipeline/                          # doit/pipeline stamps
    query.stamp
    corpus.stamp
    phrases.stamp
    clusters.stamp
  .doit.db                           # per-workdir dependency DB

temp/queries/amoc_insolation_20/     # harvest dir (name = workdir basename)
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
| `.  query` | Ran this time |
| `-- query` | Skipped (up to date) |

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
| `--limit` / `-n` | Max hits | `50` |
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
| `--kg-links` | Edge generators: `clusters`, `wikipedia`, `wikidata` | `clusters,wikipedia,wikidata` |
| `--kg-max-island` | Island size hint threshold for clean feedback | `20` |
| `--kg-min-paper-count` | Min `n_papers` (phrases_terms) for a term node | `2` |
| `--kg-max-terms` | Cap term nodes after ranking by `n_papers` | `50` |

```bash
# After clusters — interactive KG HTML (filtered terms)
pipeline kg --workdir corpora/amoc_insolation_20 \
  --kg-links clusters,wikipedia --kg-min-paper-count 2 --kg-max-terms 40 --open
```

Detail: [pipeline_encyclopedia.md](pipeline_encyclopedia.md) · [pipeline_next_encyclopedia_kg.md](pipeline_next_encyclopedia_kg.md).

---

## 6. Worked example (limit 20)

```bash
pipeline --workdir corpora/amoc_insolation_20 \
  --query "amoc AND insolation" --limit 20 \
  --phrase-method tfidf --phrase-n 3 --phrase-top 15 \
  --cluster-resolution 0.8 \
  --target clusters
```

**Plan:** `query` → `corpus` → `phrases` → `clusters`.

**Results**

- Corpus: `corpora/amoc_insolation_20/`
- Harvest: `temp/queries/amoc_insolation_20/`

**Live pytest** (same `--workdir`; uses `run --always` so it remakes instead of skipping):

```bash
pytest tests/test_pipeline.py::test_example_amoc_insolation_limit_20_to_clusters -s
```

Needs network + `doit` + `scikit-learn` + `networkx`. Marked `live_api` / `network` / `slow`.

Unit tests for the CLI use `PIPELINE_PLACEHOLDER=1` (stamps only, no network).

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

## 9. Next steps: encyclopedia + kg

- **`encyclopedia` definition:** [pipeline_encyclopedia.md](pipeline_encyclopedia.md)  
- **With `kg`:** [pipeline_next_encyclopedia_kg.md](pipeline_next_encyclopedia_kg.md)

Short version:

1. **`encyclopedia`** — select/rank phrases → Wikipedia/Wikidata; `--max-entries`, `--encyclopedia-lang`; write `encyclopedia/entries.json`.  
2. **`kg`** — edges from `--kg-links` (`clusters` \| `wikipedia` \| `wikidata`); display + islands → `clean`.

```bash
# once wired
pipeline --workdir corpora/amoc_insolation_20 \
  --encyclopedia-lang en --max-entries 50 \
  --target encyclopedia

pipeline --workdir corpora/amoc_insolation_20 \
  --kg-links clusters,wikipedia,wikidata \
  --target kg
```
