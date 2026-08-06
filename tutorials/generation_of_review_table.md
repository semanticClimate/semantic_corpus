# Generation of review table

This tutorial explains how to generate a literature review table for any query and how to review it in the browser.

The goal is to make the process easy to follow and reproducible. The workflow is simple:

1. Choose a literature query.
2. Search for papers.
3. Limit the results to 50 if you want a batch of exactly 50 papers.
4. Build the review table from the returned results.
5. Open the table in the browser and mark papers as `include`, `exclude`, or `review`.
6. Save your decisions.

This guide is meant to be readable and practical, especially if you want to show the workflow to teammates.

---

## 1. Start from scratch: create a query and output folder

If you are beginning from nothing, the workflow is:

1. Create or choose a query.
2. Choose an output folder such as `temp/queries/your_query_name`.
3. Run the search/download step so the folder contains the raw results.
4. Make sure the folder includes the expected files before building the review table.
5. Build the review table from that folder.

A typical starting point looks like this:

```python
query_name = "my_first_query"
query_string = '("climate anxiety" OR "eco anxiety")'
output_dir = Path("temp/queries/my_first_query")
```

After the search/download step, the folder should contain files such as:

```text
temp/queries/my_first_query/
├── search_results.json
├── query_run.json
└── review/
```

The review table is then built from that folder with:

```bash
./venv/bin/python scripts/build_review_table.py \
  --query-dir temp/queries/my_first_query
```

This is the simplest way to start: define the query, save the results into a dedicated folder, and then build the review table from that folder.

---

## 2. What is a review table?

A review table is a structured list of papers generated from a search result. Each row represents one paper, and each row contains metadata such as:

- title
- abstract
- authors
- journal or source
- DOI / PMCID / PMID
- whether the full text is available
- the relevance score
- the review status you assign to the paper

Once the table is built, you can quickly skim the papers and decide whether each one is worth including in the corpus.

This is useful because a raw search result is usually too large, noisy, and hard to evaluate quickly. The review table turns the list into a manageable decision-making tool.

---

## 2. Pick the query

Start by defining the exact question you want to answer with the literature search.

Examples:

```text
"climate anxiety" OR "eco anxiety"
"heat stress" AND "mental health"
"air pollution" AND "India"
```

For a table with exactly 50 papers, set the limit to 50.

```python
query_string = '("climate anxiety" OR "eco anxiety")'
limit = 50
```

A good practice is to keep each query and each output folder separate, especially if you want to compare different review batches later.

---

## 3. Search for papers and build the review table

The project already includes a workflow that searches a repository, saves the results, and builds the review table automatically.

### Example workflow

```python
from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

result = run_query_and_build_review_table(
    query_name="climate_anxiety_2026",
    query_string='("climate anxiety" OR "eco anxiety")',
    output_dir=Path("temp/queries/climate_anxiety_2026"),
    repository="europe_pmc",
    limit=50,
    formats=["xml"],
)

print(result["summary"])
print(result["review_paths"])
```

What this does:

- searches Europe PMC for matching papers
- downloads XML files if available
- writes the raw results to `search_results.json`
- writes a provenance record to `query_run.json`
- generates a review table inside `review/`

The output folder will look something like this:

```text
temp/queries/climate_anxiety_2026/
├── search_results.json
├── query_run.json
└── review/
    ├── review_table.json
    ├── review_table.csv
    ├── review_table.html
    ├── review_table.md
    └── review_table.css
```

This is the standard structure for a query batch.

---

## 4. Build the table from an existing query folder

If you already have a query folder with `search_results.json`, you can generate the review table without rerunning the search.

From the repository root:

```bash
./venv/bin/python scripts/build_review_table.py \
  --query-dir temp/queries/climate_anxiety_2026
```

This reads the search results and exports the review-table files into:

```text
temp/queries/climate_anxiety_2026/review/
```

This is useful when you want to rebuild the table after editing the query or after re-downloading papers.

---

## 5. Open the review table in the browser

Once the table is created, you should open it in the browser through the review server, not by double-clicking the HTML file directly.

Start the review server:

```bash
./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/climate_anxiety_2026/review/review_table.json \
  --query-dir temp/queries/climate_anxiety_2026
```

Then open the URL:

```text
http://127.0.0.1:8765/review_table.html
```

This is important because the browser needs to load the table and the associated paper files through the local server. Opening the raw HTML file directly may not work correctly.

---

## 6. Review the papers

Inside the review table, each row corresponds to one paper. You can then:

- skim the title and abstract
- read the full paper if needed
- mark the paper as `include`, `exclude`, or `review`
- add notes explaining the decision
- save the review table

Typical review statuses:

- `review` = still undecided
- `include` = relevant and should be kept
- `exclude` = not relevant / not suitable

When you click Save review table, all related outputs are updated together:

- `review_table.json`
- `review_table.csv`
- `review_table.html`
- `review_table.md`

The JSON file is the source of truth, while the CSV and HTML are exported views for easier review and workflow integration.

---

## 7. If you want exactly 50 papers

If your goal is to review a batch of 50 papers, use:

```python
limit = 50
```

This tells the query to return at most 50 results. The review table then contains a clean, manageable batch for screening.

For example:

```python
result = run_query_and_build_review_table(
    query_name="climate_anxiety_batch_50",
    query_string='("climate anxiety" OR "eco anxiety")',
    output_dir=Path("temp/queries/climate_anxiety_batch_50"),
    repository="europe_pmc",
    limit=50,
    formats=["xml"],
)
```

This gives one review table with 50 papers.

---

## 8. How to get a second set of 50 different papers

This is the part that often matters in practice: if you run the same query again, it usually returns the same top papers in the same order, because the repository is still ranking the same results the same way.

So if you want a different batch of 50 papers, the clean approach is to change the search in a meaningful way.

### Best option: change the date range

This is the most reproducible and easiest-to-explain approach.

Example:

```python
from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

run_query_and_build_review_table(
    query_name="climate_anxiety_2020_2023",
    query_string='("climate anxiety" OR "eco anxiety") AND (FIRST_PDATE:[2020 TO 2023])',
    output_dir=Path("temp/queries/climate_anxiety_2020_2023"),
    repository="europe_pmc",
    limit=50,
    formats=["xml"],
)
```

Then run a second batch with a different time window:

```python
run_query_and_build_review_table(
    query_name="climate_anxiety_2024_2026",
    query_string='("climate anxiety" OR "eco anxiety") AND (FIRST_PDATE:[2024 TO 2026])',
    output_dir=Path("temp/queries/climate_anxiety_2024_2026"),
    repository="europe_pmc",
    limit=50,
    formats=["xml"],
)
```

This creates two separate review tables, each with 50 papers, but with different publication windows.

### Alternative: change the wording of the query

You can also create a second batch by changing the query wording slightly while keeping the same overall topic.

Examples:

```python
'("climate anxiety" OR "eco anxiety") AND (resilience OR coping)'
```

or

```python
'("climate change" AND "anxiety" AND "mental health")'
```

This gives a different set of results, even if the broad topic remains the same.

### Recommended practice

Keep every batch in its own folder:

```text
temp/queries/climate_anxiety_2020_2023/
temp/queries/climate_anxiety_2024_2026/
```

This is clearer than overwriting the same folder and makes it much easier to compare batches.

---

## 9. Full example: generate one review table

Here is a complete example you can copy and adapt.

```python
from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

result = run_query_and_build_review_table(
    query_name="demo_review_batch",
    query_string='("climate anxiety" OR "eco anxiety")',
    output_dir=Path("temp/queries/demo_review_batch"),
    repository="europe_pmc",
    limit=50,
    formats=["xml"],
)

print("Result count:", result["result_count"])
print("Rows:", result["row_count"])
print("Output directory:", result["output_dir"])
print("Review files:", result["review_paths"])
```

Then build and open the table:

```bash
./venv/bin/python scripts/build_review_table.py \
  --query-dir temp/queries/demo_review_batch

./venv/bin/python scripts/review_viewer.py serve \
  --review-table temp/queries/demo_review_batch/review/review_table.json \
  --query-dir temp/queries/demo_review_batch
```

Open:

```text
http://127.0.0.1:8765/review_table.html
```

This is the simplest reproducible workflow for creating a review table from a query.

---

## 10. Summary

The review-table workflow is straightforward:

- choose a query
- set `limit=50` to get a batch of 50 papers
- run the search workflow
- build the review table
- review it in the browser
- save decisions

If you want a second set of 50 different papers, do not rerun the exact same query and expect a different sample automatically. Instead, change the date range or the query wording and write the output to a new folder.

This keeps the process clean, reproducible, and easy to explain to teammates.
