# Provenance: climate_anxiety_2026 corpus

## Search step (deterministic, no AI involved)

- **Repository searched:** Europe PMC
- **Query string:** `"climate anxiety" AND (HAS_FT:Y)`
- **Result limit:** 50
- **Formats requested:** xml, pdf
- **Date/time searched:** 2026-07-03T18:55:57 UTC
- **Results returned:** 50
- **Papers successfully downloaded:** 50

## How to reproduce this search

Run the following from the repository root, with the virtual environment active:

```bash
semantic_corpus download \
  --query '"climate anxiety" AND (HAS_FT:Y)' \
  --repository europe_pmc \
  --limit 50 \
  --formats xml,pdf \
  --output temp/queries/climate_anxiety_2026
```

Running this command again against Europe PMC should return the same 50 papers,
since the query and repository are fixed and deterministic — no AI or manual
judgement is involved at this stage.

## Source record

The exact parameters and result counts above are recorded in:
`temp/queries/climate_anxiety_2026/query_run.json`

The raw metadata for every matched paper (title, authors, abstract, PMCID, etc.)
is recorded in:
`temp/queries/climate_anxiety_2026/search_results.json`

## What happens after this step (not covered here)

The 50 downloaded papers were then manually reviewed by a human (include/exclude/notes),
classified into topic groups, and had candidate terms extracted. See the accompanying
`filtering_criteria.md`, `classification.md`, and `extracted_terms.md` in
`corpora/climate_anxiety_2026/data/analysis/` for that process.
