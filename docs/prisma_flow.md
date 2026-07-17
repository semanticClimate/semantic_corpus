# Tutorial-adjacent note: PRISMA-like corpus screening diagram

**Date:** 2026-07-14 (system date)  
**Status:** Implemented (v1)  
**Branch context:** developed/smoke-tested on `subhangi`

## Purpose

Build a PRISMA-like flowchart of:

query → repository → download cutoff → manual filtering → final table  

for both team documentation and manuscript figures.

## Decisions (2026-07-14)

1. **Audience:** both docs and papers (Mermaid + Graphviz DOT + optional SVG).
2. **`n_identified`:** optional overrides via `prisma_overrides.yaml` (otherwise equals retrieved).
3. **Final table:** `include` **plus** still-`review` shown separately; `n_final_table = include + still_review`.
4. **Output location:** under the corpus: `corpora/<name>/data/analysis/prisma/`.

## Honest identification counts

Without `prisma_overrides.yaml` / `query_run.total_hits`, **identified = retrieved**.
The diagram labels this as *not* a database hitCount (so we do not invent a total).

To record a true Europe PMC hit count:

```yaml
# temp/queries/<query>/prisma_overrides.yaml
n_identified: 412
notes: "Europe PMC hitCount from UI/API on 2026-07-14 (system date)"
```

## Download completeness (hard check)

Every PRISMA build runs a per-paper, per-format filesystem check against
`query_run.formats` (e.g. `xml` + `pdf`).

- **Complete:** all retrieved papers have all requested formats on disk in `query_dir`.
- **Incomplete:** CLI prints a `DOWNLOAD INCOMPLETE: ...` message, stores details in
  `prisma_flow.json` → `download_check`, and shows a **Download check** box on the diagram.
  By default the CLI **exits with status 1** after writing outputs (use
  `--allow-incomplete-downloads` to continue with success exit).

The same check is printed at the end of `run_repository_search` in the download workflow.

## Local artefacts on the diagram

Each diagram includes:

- **raw query** text
- paths to config, `query_run.json`, `search_results.json`, query dir, review table, corpus
- a **Count sources** box explaining where each number comes from

## Outputs

```
corpora/<name>/data/analysis/prisma/
  prisma_flow.json
  prisma_flow.mmd
  prisma_flow.dot
  prisma_flow.svg   # optional, via graphviz
```

## CLI

```bash
./venv/bin/python scripts/build_prisma_diagram.py \
  --corpus-dir corpora/climate_change_2026 \
  --query-dir temp/queries/climate_change_2026
```

Optional SVG:

```bash
dot -Tsvg corpora/climate_change_2026/data/analysis/prisma/prisma_flow.dot \
  -o corpora/climate_change_2026/data/analysis/prisma/prisma_flow.svg
```

## Modules

- `semantic_corpus/corpus_review/prisma_flow.py` — counts + artefacts + validation
- `semantic_corpus/corpus_review/prisma_diagram.py` — Mermaid + DOT
- `scripts/build_prisma_diagram.py` — CLI
