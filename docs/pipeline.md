# Pipeline CLI (`pipeline`)

**Date:** 2026-11-03  
**Status:** CLI + doit orchestration live; **`search` / `collect` / `corpus` / `phrases` / `pdfs` / `clusters` / `encyclopedia` / `kg` are real**; `clean` / `--source` still placeholders or partial.  
**Layout:** [bagit_structure.md](bagit_structure.md) · **Examples:** [pipeline_examples.md](pipeline_examples.md)  
**Tutorials:** [resume + lazy PDFs](tutorials/pipeline_epmc_resume.md) · [lazy PDFs](tutorials/lazy_pdfs.md) · [KG from query](tutorials/kg_from_query.md)  
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
                        ├──► search ──► paper:* ──► collect ──► corpus (+indexes)
--source (static docs) ─┘                                      │
(neither) ──────────────────────────────────────────────► corpus …
                                                               ▼
                                                         phrases ──► clusters [--kg→KG₁]
                                                           │              │
                                                           └──► pdfs      ▼
                                                                        clean
                                                                          │
                                                                          ▼
                                                                encyclopedia [--kg→KG₂]
# design: two display KGs via --kg flag (not a step); clean after clusters
# detail: docs/pipeline_kg_mappers.md
```

| Step | Design role | Implementation today |
|------|-------------|----------------------|
| `search` | Hit list only | `query.json` + `search_results.json` |
| `collect` | Per-paper JSON+XML | `data/packets/`; resume; no PDF; `--source` placeholder |
| `corpus` | Corpus gate **+** packet indexes | BagIt/packets load + `data/indexes/packets.json` |
| `phrases` | Traverse indexed texts → terms | Real (`step2` → `data/indexes/phrases/`) |
| `pdfs` | Lazy PDF fill | Real; `--paper-id` for one paper; optional Docling |
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

`--workdir` is a **BagIt bag root**. Packet bytes live under ``data/packets/``;
reduce products under ``data/indexes/``. Filenames encode type and transform
history (left → right). Full contract: [bagit_structure.md](bagit_structure.md).

| Pattern | Meaning |
|---------|---------|
| `{id}.json` | Metadata / abstract (JSON stream) |
| `{id}.xml` | Publisher / EPMC fullTextXML |
| `{id}.pdf` | Native PDF (**lazy**; usually gitignored) |
| `{id}.pdf.xml` | Docling: PDF → XML |
| `{id}.pdf.html` | Docling: PDF → HTML (optional) |

For `--workdir corpora/amoc_insolation_20`:

```text
corpora/amoc_insolation_20/          # --workdir = bag root
  bagit.txt
  query.json
  search_results.json
  corpus.json
  pipeline/                          # stamps + doit.db
  data/
    packets/                         # MAP
      PMC12345.json
      PMC12345.xml
      PMC12345.pdf                   # optional / lazy
      PMC12345.pdf.xml
    indexes/                         # REDUCE
      packets.json
      phrases/
      clusters/
```

**Collect** fetches JSON+XML only. **`pdfs`** fills PDFs later (`--paper-id` for one paper).

**Packet text cascade:** prefer `{id}.xml`, else `{id}.pdf.xml`, else abstract in `{id}.json`.

**Partial completion / resume**

| Layer | Mechanism |
|-------|-----------|
| Per file | Valid target exists → skip that format (never overwrite) |
| Per paper (collect) | Done when `{id}.json` + XML/pdf.xml, or recorded `_collect_xml` miss |
| Per paper (pdfs) | Skip if valid `{id}.pdf` exists |
| Interrupt | Ctrl-C leaves written files; re-run continues from the next incomplete paper |

Doit graph: `search` → `paper:{id}` → `collect` → `corpus` → `phrases` → …; `pdfs` parallel after `corpus`.

---

## 4. Skip-if-done (why a re-run can take seconds)

Like Make/doit: if stamps and key artifacts are already current, steps are **skipped**.

| Output | Meaning |
|--------|---------|
| `.  collect` | Ran this time |
| `-- collect` | Skipped (up to date) |
| `.  paper:PMC…  [ok]` | Fetched this run (XML ok) |
| `.  paper:PMC…  [xml=500]` | Tried this run; Europe PMC returned HTTP 500 |
| `-- paper:4287…  [no_pmcid]` | Skipped; PMID-only (metadata already saved) |

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

Note: even with `--always`, the downloader still reuses valid flat files
(`{id}.json|.xml|.pdf|.pdf.xml`) already present under `--workdir`.

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
