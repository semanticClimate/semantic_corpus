# Record: HTML review table and paper reader

**Date:** 2026-07-04  
**Status:** Implemented and verified  
**Example corpus:** `climate_anxiety_2026` (50 papers)

## Summary

Human reviewers can browse, read full papers, and record include/exclude decisions in a browser — without Excel or copying paper text into HTML files.

| Role | File | Notes |
|------|------|-------|
| Source of truth | `review/review_table.json` | All tools read/write this |
| Machine export | `review/review_table.csv` | Pipelines only; do not edit by hand |
| Human editing | `review/review_table.html` | Status + notes in a table |
| Styling | `review/review_table.css` | Optional; user-editable |
| Read-only overview | `review/review_table.md` | Quick scan |

Full papers (PDF/HTML) stay on disk under the query directory and/or BAGIT corpus. The review UI loads them through a local HTTP server — never embedded in the HTML export.

## User-facing tools

| Tool | Command | Purpose |
|------|---------|---------|
| Build table | `scripts/build_review_table.py` | Generate json/csv/md/html/css from query output |
| Serve + edit | `scripts/review_viewer.py serve` | **Required** for saving and reading papers |
| Paper-by-paper | `review_viewer.html` (optional) | Sidebar walk-through with Y/N buttons |
| Terminal review | `scripts/interactive_review.py` | Alternative to HTML |

## Architecture

```
search_results.json + {pmcid}.xml/.pdf
        │
        ▼
build_review_table.py
        │
        ▼
review/review_table.json  ◄── source of truth
        │
        ├── export → .csv, .md, .html, .css
        │
        └── review_viewer.py serve (port 8765)
                 │
                 ├── GET  /review_table.html      editable table
                 ├── GET  /api/health             connection check
                 ├── GET  /api/paper-preview      abstract + file URLs
                 ├── GET  /papers/{pmcid}.pdf     full PDF (Range support)
                 ├── GET  /papers/{pmcid}.html    full HTML from corpus
                 └── POST /api/save               writes all exports
```

### Design decisions

1. **CSV export, HTML edit** — spreadsheets are for interchange; reviewers use the browser table.
2. **No full-text copy in HTML** — only metadata rows are embedded; papers fetched on demand.
3. **Side panel reader** — table stays visible; selected row highlighted; PDF/HTML toggle in panel header.
4. **Serve mode mandatory for papers** — opening `review_table.html` via `file://` cannot load PDFs; page shows a red connection banner.
5. **PDF via fetch + blob URL; HTML via fetch + iframe srcdoc** — avoids browser iframe/plugin issues with bare URLs.
6. **HTTP Range (206) for PDFs** — required by Chrome’s embedded PDF viewer.
7. **Score hidden in UI** — score remains in JSON/CSV; can hide column via CSS (`.col-score { display: none }`).

## Key code paths

| Component | Path |
|-----------|------|
| Table export | `semantic_corpus/corpus_review/review_table.py` |
| Default CSS | `semantic_corpus/corpus_review/assets/review_table.css` |
| HTTP server | `semantic_corpus/corpus_review/review_viewer_server.py` |
| Paper-by-paper viewer | `semantic_corpus/corpus_review/html_viewer.py` |
| Document paths | `semantic_corpus/corpus_review/text_preview.py` |
| CLI serve/build | `scripts/review_viewer.py` |

## Example paths (climate anxiety)

```
config/climate_anxiety_2026.yaml
temp/queries/climate_anxiety_2026/search_results.json
temp/queries/climate_anxiety_2026/PMC*.pdf
temp/queries/climate_anxiety_2026/review/review_table.json
temp/queries/climate_anxiety_2026/review/review_table.html
corpora/climate_anxiety_2026/data/documents/html/europe_pmc_*.html
```

## Tests

- `tests/test_review_table_html.py`
- `tests/test_review_viewer_server.py` (health, Range, document resolve)
- `tests/test_text_preview_paths.py`
- `tests/test_html_review_viewer.py`

## Related docs

- Tutorial: [../tutorials/html_review_table_tutorial.md](../tutorials/html_review_table_tutorial.md)
- Build reference: [../build_review_table.md](../build_review_table.md)
- Terminal review: [../interactive_review.md](../interactive_review.md)
