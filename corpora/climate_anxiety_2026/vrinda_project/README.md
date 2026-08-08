# Vrinda's ORAT Project — Climate Anxiety Corpus

This folder documents my work on the `climate_anxiety_2026` corpus for the ORAT subproject.

## Contents

- `climate_anxiety_2026/provenance/` — how the 50 papers were found (query, repository, date, reproducibility instructions)
- `climate_anxiety_2026/review/` — the reviewed table (35 include, 9 exclude, 6 flagged), with notes explaining each decision
- `climate_anxiety_2026/analysis/` — filtering criteria, topic classification, and extracted terms from the included papers

## Workflow summary

1. Searched Europe PMC for `"climate anxiety" AND (HAS_FT:Y)`, limit 50
2. Built a review table using `scripts/build_review_table.py`
3. Reviewed each paper manually (include/exclude/notes) via `scripts/review_viewer.py serve`
4. Classified included papers into topic groups
5. Extracted candidate terms for the ORAT vocabulary
