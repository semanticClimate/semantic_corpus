# Tutorial: Review papers in the HTML table

**Audience:** Team members reviewing a query result before building a corpus  
**Time:** ~15 minutes  
**Example:** `climate_anxiety_2026` (50 papers, already downloaded)

## What you will do

1. Build (or refresh) a review table from a query folder
2. Start the local review server
3. Open the table in your browser at an **http://** URL
4. Read full papers (PDF or HTML), set **include** / **exclude**, add notes, and save

You do **not** need Excel. You do **not** edit `review_table.csv` by hand.

---

## Before you start

From the repository root, with the virtualenv active:

```bash
cd /path/to/semantic_corpus
source venv/bin/activate   # or use ./venv/bin/python below
```

You need a query output directory containing at least:

- `search_results.json`
- `{pmcid}.xml` and/or `{pmcid}.pdf` (when downloads succeeded)
- optionally `query_run.json` (provenance)

For this tutorial we use:

```
temp/queries/climate_anxiety_2026/
```

---

## Step 1 — Build the review table

```bash
./venv/bin/python scripts/build_review_table.py \
  --query-dir temp/queries/climate_anxiety_2026
```

Expected output:

```
Rows: 50 ...
  json: temp/queries/climate_anxiety_2026/review/review_table.json
  csv:  ...
  html: temp/queries/climate_anxiety_2026/review/review_table.html
  css:  temp/queries/climate_anxiety_2026/review/review_table.css
```

**Source of truth:** `review_table.json`. Everything else is derived from it.

---

## Step 2 — Start the review server

**Important:** Papers only load when the page is served over HTTP — not when you double-click the HTML file.

```bash
./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
  --query-dir temp/queries/climate_anxiety_2026
```

The script prints something like:

```
Review tools: http://127.0.0.1:8765/
  Table (edit): http://127.0.0.1:8765/review_table.html
  Open this URL: http://127.0.0.1:8765/review_table.html
```

Your browser may open that URL automatically. If not, copy it into the address bar.

Leave this terminal running while you review.

---

## Step 3 — Check the connection banner

At the top of the page you should see:

- **Green banner** — “Connected to review server at `http://127.0.0.1:8765`…” → you are ready
- **Red banner** — you opened a saved file (`file://…`) or the server is not running → go back to Step 2

If you see red, do **not** open the file from Finder or the IDE file preview. Use the **http://** link only.

---

## Step 4 — Explore the table

The table has one row per paper. Key columns:

| Column | What to do |
|--------|------------|
| **Status** | `review` (undecided), `include`, or `exclude` |
| **Title / Abstract** | Skim relevance |
| **Read** | **PDF** / **HTML** links open full text in a new tab; **Read** opens the side panel |
| **Notes** | Free text (why you included/excluded) |

Try sorting mentally by title, or scroll to a paper that looks interesting.

---

## Step 5 — Read a full paper

In the **Read** column each row has:

- **PDF** / **HTML** — click to open full text in a **new browser tab**
- **Read** — opens the **side panel** (row highlighted in blue)

For the side panel:

1. Click **Read** on any row with a PMCID.
2. Use **PDF** or **HTML** in the panel header to switch format.
3. Click **Close**, the backdrop, or press **Esc** to return to the table.

Papers are loaded from disk through the server. They are not copied into the HTML file.

---

## Step 6 — Record your decision

For each paper:

1. Set **Status** to `include` or `exclude` (or leave as `review` if unsure).
2. Add **Notes** if helpful (e.g. “not about climate anxiety”, “good methods section”).
3. Click **Save review table** at the bottom.

Save updates **all** of these together:

- `review_table.json`
- `review_table.csv`
- `review_table.html`
- `review_table.md`

You can save as often as you like.

---

## Step 7 — Customise appearance (optional)

Edit styling in the same folder:

```
temp/queries/climate_anxiety_2026/review/review_table.css
```

Reload the browser page to see changes. Your CSS is kept on rebuild unless the file did not exist yet.

Examples:

```css
/* Wider title column */
.col-title { max-width: 40rem; }

/* Hide score if added to table later */
.col-score { display: none; }
```

---

## Step 8 — Use your decisions downstream

Filter included papers programmatically:

```python
import json
from pathlib import Path

rows = json.loads(Path("temp/queries/climate_anxiety_2026/review/review_table.json").read_text())
included = [r for r in rows if r["review_status"] == "include"]
print(len(included), "papers to ingest")
```

Or open `review_table.csv` in another tool — but always treat **JSON as authoritative**.

---

## Alternative: one paper at a time

If you prefer a sidebar queue with Include / Exclude buttons:

```
http://127.0.0.1:8765/review_viewer.html
```

Same server, same save endpoint. Most reviewers will prefer **review_table.html** for seeing all papers at once.

Terminal-only option: [interactive_review.md](../interactive_review.md).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| Red connection banner | Opened `file://` path or server stopped | Run Step 2; use `http://127.0.0.1:8765/review_table.html` |
| Blank side panel | Server not connected | Check green banner first |
| “Failed to load PDF/HTML” | Missing file on disk | Check `has_pdf` / `has_xml` columns; re-run download workflow |
| Save downloads JSON instead of saving in place | Not using serve mode | Use `review_viewer.py serve` |
| CSS looks wrong after updates | Old patched CSS | Re-run `build_review_table.py`; edit `review_table.css` again |

For bugs, note: command run, URL in address bar (http vs file), banner colour, and what you clicked.

---

## Quick reference (copy-paste)

```bash
# Build
./venv/bin/python scripts/build_review_table.py \
  --query-dir temp/queries/climate_anxiety_2026

# Serve (keep running)
./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
  --query-dir temp/queries/climate_anxiety_2026

# Open in browser
# http://127.0.0.1:8765/review_table.html
```

---

## Further reading

- **New member quick start:** [new_member_review_quickstart.md](new_member_review_quickstart.md)
- Feature record: [../records/2026-07-04_html_review_table.md](../records/2026-07-04_html_review_table.md)
- Discussion summary: [../summary/2026-07-06_review_workflow.md](../summary/2026-07-06_review_workflow.md)
- Build options: [../build_review_table.md](../build_review_table.md)
- Full AQI workflow example: [../aqi_india_corpus_workflow.md](../aqi_india_corpus_workflow.md)
