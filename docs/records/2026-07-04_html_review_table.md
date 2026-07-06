# Record: HTML review table and paper reader

**Date:** 2026-07-04 (initial); updated 2026-07-06  
**Status:** Implemented and verified  
**Example corpus:** `climate_anxiety_2026` (50 papers)

**Discussion summary:** [../summary/2026-07-06_review_workflow.md](../summary/2026-07-06_review_workflow.md)  
**New member guide:** [../tutorials/new_member_review_quickstart.md](../tutorials/new_member_review_quickstart.md)

## Summary

Human reviewers browse, read full papers, and record include/exclude decisions in a browser — without Excel or copying paper text into HTML files.

| Role | File | Notes |
|------|------|-------|
| Source of truth | `review/review_table.json` | All tools read/write this |
| Machine export | `review/review_table.csv` | Pipelines only; do not edit by hand |
| Human editing | `review/review_table.html` | Status + notes in a table |
| Styling | `review/review_table.css` | Optional; user-editable |
| Read-only overview | `review/review_table.md` | Quick scan |

Full papers (PDF/HTML) stay on disk under the query directory and/or BAGIT corpus. The review UI loads them through a local HTTP server — never embedded in the HTML export.

## Read column (current behaviour)

Each row’s **Read** column contains:

| Control | Behaviour |
|---------|-----------|
| **PDF** link | `GET /papers/{pmcid}.pdf` — opens in new tab |
| **HTML** link | `GET /papers/{pmcid}.html` — opens in new tab |
| **Read** button | Opens side panel; loads PDF (default) or HTML via panel toggle |

Requires `review_viewer.py serve` (http:// URL). A green connection banner confirms the server is reachable.

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
                 ├── GET  /papers/{pmcid}.pdf     full PDF (HTTP Range 206)
                 ├── GET  /papers/{pmcid}.html    full HTML from corpus
                 └── POST /api/save               writes all exports
```

Corpus documents are resolved from:

- `temp/queries/{query}/{pmcid}.pdf` (query download)
- `corpora/{name}/data/documents/{pdf,html,xml}/`
- `corpora/{name}/data/data/documents/...` (nested BAGIT layout)

Corpus dir is auto-inferred from query folder name when not passed explicitly.

### Design decisions

1. **CSV export, HTML edit** — spreadsheets are for interchange; reviewers use the browser table.
2. **No full-text copy in HTML** — only metadata rows are embedded; papers fetched on demand.
3. **Side panel reader** — table stays visible; selected row highlighted; PDF/HTML toggle in panel header.
4. **Direct PDF/HTML links** — real `<a href>` per row as well as panel button.
5. **Serve mode mandatory for papers** — `file://` shows red banner; cannot load or save in place.
6. **PDF via fetch + iframe blob URL; HTML via fetch + iframe srcdoc** — reliable across browsers.
7. **HTTP Range (206) for PDFs** — required by Chrome’s PDF viewer.
8. **Score hidden in UI** — score remains in JSON/CSV.

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
corpora/climate_anxiety_2026/data/data/documents/html/europe_pmc_*.html
```

## Tests

- `tests/test_review_table_html.py`
- `tests/test_review_viewer_server.py` (health, Range, document resolve)
- `tests/test_text_preview_paths.py` (nested corpus paths)
- `tests/test_html_review_viewer.py`

## Related docs

- Quick start: [../tutorials/new_member_review_quickstart.md](../tutorials/new_member_review_quickstart.md)
- Full tutorial: [../tutorials/html_review_table_tutorial.md](../tutorials/html_review_table_tutorial.md)
- Build reference: [../build_review_table.md](../build_review_table.md)
- Terminal review: [../interactive_review.md](../interactive_review.md)
