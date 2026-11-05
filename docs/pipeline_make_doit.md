# Pipeline orchestration: Make, doit, and alternatives

**Date:** 2026-11-03  
**Status:** Decision record — prefer **doit** for symbolic, skip-if-done cluster-review steps  
**Related:** [pipeline.md](pipeline.md) (user tutorial / CLI), [pipeline_design.md](pipeline_design.md) (detailed symbolic pipeline), [cluster_filtering_workflow.md](cluster_filtering_workflow.md), [cluster_review_steps_0_3_progress.md](cluster_review_steps_0_3_progress.md)

---

## Problem

Cluster-review Steps 0–6 are evolving (BKG clean, encyclopedia KG; **no Step 7**). Numeric CLI flags such as `--from-step 2` / `--to-step 2` will break when steps are renamed or reordered.

We need:

1. **Stable symbolic targets** (`query`, `corpus`, `phrases`, `clusters`, …)  
2. **Make-like skip-if-done** — if artifacts are already current, do not re-run  
3. A tool that works from the **command line** and can be triggered from **Streamlit**

---

## Options surveyed

None of these were already dependencies of `semantic_corpus` at the time of this note (`doit` / `snakemake` / `invoke` not installed).

| Tool | Skip-if-done? | Symbolic targets? | Fit for this repo |
|------|---------------|-------------------|-------------------|
| **[doit](https://pydoit.org/)** (pydoit) | Yes — `file_dep` / `targets` / custom `uptodate` (MD5 or mtime) | Yes (`doit phrases`) | **Best Make-like match in pure Python** |
| **GNU Make** | Yes (mtime of files) | Yes | Awkward for parameterized corpus paths and calling Python library APIs |
| **Snakemake** | Yes | Rule names | Strong for scientific data workflows; heavier than a 6-step local pipeline |
| **Invoke** | No incremental DAG | Yes | Task runner only — always re-runs unless you hand-roll checks |
| **Just** | No real Make-style DAG cache | Yes | Convenient recipes; not skip-if-done |
| **Cook / ntask** | Yes (content-hash) | Yes | Newer / smaller ecosystem |
| **Luigi / Prefect / Dagster** | Different orchestration model | Yes | Service-style orchestrators — too heavy |
| **Custom `pipeline.py` “mini-make”** | We would invent it | Yes | Avoids a dependency but reimplements what **doit** already does |

### Notes on the main contenders

**doit**  
- Tasks are plain Python (`task_*` functions returning dicts).  
- Tracks dependencies and targets; skips up-to-date work.  
- Supports custom `uptodate` callables (e.g. phrase-index params match).  
- Can be driven as a **library** via `DoitMain` / `ModuleTaskLoader` (important for Streamlit).  
- Mature, documented, previously used in this community.

**GNU Make**  
- Ubiquitous and familiar.  
- Timestamp-based rules struggle with “corpus_dir is a parameter” and with “skip extract if `phrases/index.json` params match paper set”.  
- Fine as a thin wrapper later (`make phrases` → `doit phrases`); not ideal as the primary engine.

**Snakemake**  
- Excellent for large bioinformatics-style artifact graphs, conda/containers, clusters.  
- Overkill for calling a handful of existing Python functions on one BAGIT corpus.

**Homegrown Python make**  
- Tempting for zero deps.  
- Duplicates doit’s dependency DB, force/rebuild semantics, and CLI.  
- Rejected unless an explicit “no new dependency” constraint appears.

---

## Decision

**Use doit** for symbolic targets and skip-if-done. Do **not** invent a custom make.

- Add `doit` to optional extras (e.g. `[cluster_review]`).  
- Deprecate numeric `--from-step` / `--to-step` in favour of named targets.  
- Keep Streamlit stage **numbers** only as UI order labels; execution goes through named doit tasks.

---

## Compatibility with Streamlit

**Yes — compatible**, with a clear split of roles:

| Layer | Responsibility |
|-------|----------------|
| **Streamlit** | UI, session state, buttons, display of results |
| **doit** | Dependency graph, up-to-date checks, running/skipping tasks |

### How to call doit from Streamlit

- Prefer **`DoitMain(ModuleTaskLoader(...)).run([...])`**, which returns an exit code.  
- Avoid **`doit.run(globals())`** inside the app — it calls **`sys.exit()`** and would kill the Streamlit process.  
- Trigger named targets from button callbacks, e.g. ensure `phrases` or `clusters`.  
- Keep task **actions** as in-process library calls (`extract_phrases`, `build_clusters`, …), not subprocess launches of Streamlit.  
- Store doit’s dependency DB **per corpus but outside the BAGIT root**
  (e.g. `temp/pipeline_doit/<name>_<hash>/doit.db`).  
  `bagit.make_bag` moves every top-level file into `data/`; a DB under
  `corpora/<name>/.doit.db` gets swept away mid-run and then fails on Windows
  when doit tries to dump state (`FileNotFoundError: …\.doit.db.dat`).  
- Be cautious with doit’s multiprocess `-n` from inside Streamlit; default to sequential runs from the UI.

Streamlit does **not** need to embed a doit UI; it only needs to invoke the same tasks the CLI uses.

---

## Proposed task graph (symbols)

Stable IDs (independent of UI step numbers):

| Task | Meaning | “Current” when (sketch) |
|------|---------|-------------------------|
| `query` | Harvest literature → query dir (+ optional BAGIT create) | `search_results.json` (and bag if requested) |
| `corpus` | Ensure / load BAGIT corpus (produced by query/documents) | `bagit.txt` + ≥1 metadata paper |
| `phrases` | Keyphrase extract (TF-IDF default) | `phrases/index.json` matches paper set + params |
| `clusters` | Bipartite KG (BKG) + Louvain | `clusters/graph_summary.json` ≥ phrases index |
| `update_pdfs` | Fill missing PDFs into the bag | Per-file skip (existing `update_bagit_formats`) |
| `clean` | BKG FP paper/term cleaning *(planned)* | Decision stamps when implemented |
| `orphans` | Orphan review + export *(planned)* | Export / decision stamps |
| `encyclopedia` | Wikipedia/Wikidata KG *(optional partner to clean)* | Encyclopedia artifacts |

Default chain: `query → bagit → phrases → clusters` (then planned `clean → orphans`; `encyclopedia` optional).

Example CLI (placeholders; see [pipeline.md](pipeline.md)):

```bash
# Ensure through clusters; skip steps already current
pipeline --workdir temp/demo --query "AMOC AND India" --limit 50 --target clusters

# Remake phrases (then dependents on next ensure)
pipeline forget phrases && pipeline clusters

# From Streamlit later: same ModuleTaskLoader + DoitMain(["run", "clusters"])
```

---

## Implementation sketch (not yet required by this doc)

1. Task module defining `task_query`, `task_bagit`, `task_phrases`, `task_clusters`, … with `file_dep` / `targets` / `task_dep` / `uptodate`.  
2. Actions call existing APIs in `semantic_corpus.cluster_review`.  
3. Thin CLI entry (or `python -m doit -f …`) plus Streamlit buttons.  
4. Remove or hard-error numeric `--from-step` / `--to-step` with a pointer to symbols.  
5. Document symbols next to the workflow diagram in [cluster_filtering_workflow.md](cluster_filtering_workflow.md).

---

## What we are not doing

- Replacing the cluster-review library with a workflow engine  
- Putting KBIR / encyclopedia build inside the phrase extract task  
- Adding a homemade make in `pipeline.py` as the long-term solution  

---

## References

- [pydoit — Python Task Runner](https://pydoit.org/)  
- [doit dependencies / uptodate](https://pydoit.org/dependencies.html)  
- [Using doit as a framework (DoitMain / TaskLoader)](https://pydoit.org/extending.html)  
- [Snakemake](https://snakemake.github.io/)  
- Software Carpentry: [Make vs doit](https://github.com/swcarpentry/bc/blob/gh-pages/intermediate/doit/make-vs-doit.md)  
