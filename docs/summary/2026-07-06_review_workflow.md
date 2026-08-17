# Summary: HTML review table workflow (July 2026)

**Date:** 2026-07-04 – 2026-07-06  
**Topic:** Browser-based corpus paper review for `climate_anxiety_2026`  
**Status:** Working; documented for onboarding

## Problem we solved

Reviewers needed to:

- Export review data as **CSV** for downstream tools
- **Edit decisions in HTML** (not Excel), on any platform
- **Read full papers** (PDF or HTML) while reviewing
- Avoid duplicating paper text into review files

## Solution overview

```
Query download  →  build_review_table.py  →  review_table.json
                                                    ↓
                              review_viewer.py serve (port 8765)
                                                    ↓
                              review_table.html in browser
                              (edit status + notes, read papers, save)
```

## What we built

### Review table exports (`build_review_table.py`)

| Output | Purpose |
|--------|---------|
| `.json` | Source of truth |
| `.csv` | Machine export only |
| `.html` | Human editing UI |
| `.css` | User-customisable styling |
| `.md` | Read-only overview |

### Browser review (`review_viewer.py serve`)

- Serves `review_table.html` over **http://127.0.0.1:8765**
- **Green/red connection banner** — detects `file://` vs server
- **Read column:** `PDF` / `HTML` links (new tab) + `Read` button (side panel)
- **Side panel:** PDF/HTML toggle; selected row highlighted
- **Save:** writes json, csv, html, md together
- **Papers served from disk** via `/papers/{pmcid}.pdf` and `.html` — not embedded in HTML

### Optional: paper-by-paper viewer

`review_viewer.html` — sidebar queue with Include/Exclude. Same server. Most reviewers use the **table**.

### Terminal alternative

`interactive_review.py` — Y/N in the shell. See [interactive_review.md](../interactive_review.md).

## Design principles (agreed in review)

1. **JSON is authoritative** — CSV is a mirror for pipelines.
2. **HTML is for humans** — styled via external CSS.
3. **No full-text in HTML exports** — previews and papers loaded on demand.
4. **Score not shown in UI** — still in JSON/CSV; relevance score considered unreliable for manual review.
5. **HTTP server required** — `file://` cannot load PDFs or save in place.

## Issues encountered and fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| 0 PDFs from Europe PMC | Wrong PDF URL | Use `?pdf=render` endpoint |
| “Paper 1 of 0” in viewer | Stale queue filter | Fixed navigation; removed score filter from UI |
| review_viewer copied all abstracts | Embedded full text at build | Load preview via `/api/paper-preview` on demand |
| PDF/HTML blank in panel | `file://` open; iframe height; missing Range headers; `<embed>` unreliable | Server-only URL; inline flex CSS; HTTP 206; single iframe + fetch/blob |
| HTML not found | Nested `data/data/documents/` in corpus | Path resolver checks both layouts |
| Read buttons “don’t link” | JS-only button; no direct URLs | Added **PDF** / **HTML** anchor links per row |
| New member opened wrong table | Empty AQI pilot table | Point to `climate_anxiety_2026` example |

## Example corpus for demos

**Query:** `"climate anxiety" AND (HAS_FT:Y)` — `config/climate_anxiety_2026.yaml`

```
temp/queries/climate_anxiety_2026/review/review_table.json   ← 50 papers
temp/queries/climate_anxiety_2026/review/review_table.html
corpora/climate_anxiety_2026/data/documents/                 ← full text files
```

Do **not** use `corpora/aqi_india_pilot/.../review_table.md` as a demo — it has no data rows yet.

## Documentation map

| Doc | Audience |
|-----|----------|
| [tutorials/new_member_review_quickstart.md](../tutorials/new_member_review_quickstart.md) | New team member (5 min) |
| [tutorials/html_review_table_tutorial.md](../tutorials/html_review_table_tutorial.md) | Full walkthrough (~15 min) |
| [records/2026-07-04_html_review_table.md](../records/2026-07-04_html_review_table.md) | Architecture / implementers |
| [build_review_table.md](../build_review_table.md) | Build script reference |

## Quick commands (climate anxiety)

```bash
./venv/bin/python scripts/build_review_table.py \
  --query-dir temp/queries/climate_anxiety_2026

./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
  --query-dir temp/queries/climate_anxiety_2026
# → http://127.0.0.1:8765/review_table.html
```

## Future work (mentioned, not done)

- HTML section selection for reviewers (build on HTML reader)
- Round-trip editing from CSV (not requested; JSON/HTML preferred)
