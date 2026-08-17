# Quick start: Review a query (new team members)

**Time:** 5 minutes to first paper  
**Worked example:** `climate_anxiety_2026` (50 papers)

## What you are looking at

After a literature search is downloaded, the team builds a **review table** — one row per paper. You decide which papers go into the corpus (`include` / `exclude`) and add notes.

| File | You should… |
|------|-------------|
| `review_table.json` | Treat as source of truth (tools use this) |
| `review_table.csv` | Ignore for editing (export for pipelines only) |
| `review_table.html` | **Edit here** (in browser, via server) |

**Example table (first rows):**

| status | title | pmcid | has_pdf |
|--------|-------|-------|---------|
| review | Psychological resilience as a buffer against climate change anxiety… | PMC12959560 | yes |
| review | An Adolescent-Caregiver Dyad Approach to Climate Anxiety… | PMC12789392 | yes |

Full file: `temp/queries/climate_anxiety_2026/review/review_table.md`

---

## Three commands

```bash
cd /path/to/semantic_corpus

# 1. Build the table (once per query, or after re-download)
./venv/bin/python scripts/build_review_table.py \
  --query-dir temp/queries/climate_anxiety_2026

# 2. Start the review server (keep this terminal open)
./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
  --query-dir temp/queries/climate_anxiety_2026

# 3. Open in your browser (must be http://, not a saved file)
#    http://127.0.0.1:8765/review_table.html
```

Check for a **green banner** at the top (“Connected to review server”). If it is **red**, you opened the HTML file from disk — use the http:// URL instead.

---

## How to review one paper

1. Skim **Title** and **Abstract** in the table.
2. Open full text — in the **Read** column:
   - **PDF** or **HTML** → opens in a new browser tab
   - **Read** → opens a side panel (row highlighted in blue)
3. Set **Status** to `include` or `exclude` (or leave `review`).
4. Add **Notes** if useful.
5. Click **Save review table** at the bottom.

---

## Rules of thumb

- **Always use the server URL** — double-clicking `review_table.html` will not load papers.
- **Do not edit the CSV** — use the HTML table or edit JSON if you are scripting.
- **Papers are not copied into the HTML** — PDF/HTML are read from disk when you click Read.
- **Score column** is omitted from the UI by design; it remains in JSON/CSV for tooling.

---

## If something breaks

| Problem | Fix |
|---------|-----|
| Red banner | Start `review_viewer.py serve`; open http://127.0.0.1:8765/review_table.html |
| PDF/HTML links do nothing | Same as above — need http:// server |
| Blank panel | Hard-refresh (Cmd+Shift+R); confirm green banner |
| Empty AQI table | Use `climate_anxiety_2026` example, not `aqi_india_pilot` (no rows yet) |

---

## Full tutorial

Step-by-step with screenshots-level detail: [html_review_table_tutorial.md](html_review_table_tutorial.md)

Technical background: [../records/2026-07-04_html_review_table.md](../records/2026-07-04_html_review_table.md)

Discussion summary: [../summary/2026-07-06_review_workflow.md](../summary/2026-07-06_review_workflow.md)
