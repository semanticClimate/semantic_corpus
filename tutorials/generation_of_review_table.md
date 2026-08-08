# Generation of review table

This tutorial explains how to generate a literature review table from scratch and how to review it in the browser.

If you are brand new to this project, the easiest way to think about it is:

1. Clone the repository.
2. Open the repository on your computer.
3. Install the Python dependencies.
4. Run a small Python script that searches for papers.
5. Save the results into a dedicated folder.
6. Build a review table from that folder.
7. Open the review table in the browser and mark papers as `include`, `exclude`, or `review`.
8. Save your decisions.

This guide is meant to be readable and practical, especially if you want to show the workflow to teammates.

---

## 1. Start from scratch

If you are getting started for the first time, follow these steps in order.

### 1.1 Clone the repository

Clone the repository from GitHub:

```bash
git clone https://github.com/semanticClimate/semantic_corpus.git
cd semantic_corpus
```

This creates a folder called `semantic_corpus` on your computer. This is the main project folder. Everything you do for this workflow should happen inside this folder.

### 1.2 Check Python

Make sure Python is available:

```bash
python --version
```

If Python is not installed, install Python 3.10 or newer first.

### 1.3 Create a virtual environment

Inside the repository folder, create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

On Windows, use:

```powershell
.venv\Scripts\activate
```

A virtual environment keeps the project dependencies isolated from the rest of your computer.

### 1.4 Install the package and dependencies

From the repository root, install the project:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

This installs the package and its dependencies so the scripts in this repository can run.

### 1.5 Create a folder for your first query

Create a dedicated output folder for your work:

```bash
mkdir -p temp/queries/my_first_query
```

This is where the search results and review files will live. A good habit is to give each batch its own folder, for example:

```text
temp/queries/my_first_query/
```

### 1.6 Put the query code in a Python file

For a first run, create a simple Python file in the repository root, next to files such as `README.md` and `pyproject.toml`.

That means the file should live here:

```text
semantic_corpus/my_first_query.py
```

Open that file in a text editor and paste in the following code:

```python
from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

result = run_query_and_build_review_table(
    query_name="my_first_query",
    query_string='("climate anxiety" OR "eco anxiety")',
    output_dir=Path("temp/queries/my_first_query"),
    repository="europe_pmc",
    limit=50,
    formats=["xml"],
)

print(result["summary"])
print(result["review_paths"])
```

Then run it from the terminal while you are inside the repository folder:

```bash
python my_first_query.py
```

This tells Python to execute the code in `my_first_query.py` from the repository root. The script will search the repository, save the output files into `temp/queries/my_first_query`, and build the review table from there.

### 1.7 What files should appear?

After the script runs, your output folder should contain files similar to this:

```text
temp/queries/my_first_query/
├── search_results.json
├── query_run.json
└── review/
    ├── review_table.json
    ├── review_table.csv
    ├── review_table.html
    ├── review_table.md
    └── review_table.css
```

If you want to rebuild the review table later from the same folder, run:

```bash
./venv/bin/python scripts/build_review_table.py \
  --query-dir temp/queries/my_first_query
```

This is the simplest way to start: choose a query, save the results into a dedicated folder, and then build the review table from that folder.

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

## 8. Duplicate the query for a different batch of papers

If you want a second set of papers, the clean approach is to duplicate the query workflow rather than overwrite the first batch.

That means:

1. keep the first batch in one folder,
2. create a second folder for the next batch,
3. change the query slightly or adjust the date range,
4. run the search again,
5. then combine the results into one review table if you want both batches to appear together.

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

This gives you a second, different batch of papers.

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

## 9. Add a second batch to the same review table

If you want the next batch to appear in the same review table, treat the first and second batch as two input sources and merge them into one review table.

In practice, that means:

1. build the first review table in one folder,
2. build the second review table in another folder,
3. load both `review_table.json` files,
4. combine the rows into one list,
5. export that combined list again as `review_table.json`, `review_table.csv`, and `review_table.html`.

Here is a simple example:

```python
import json
from pathlib import Path
from semantic_corpus.corpus_review.review_table import export_review_tables

base_dir = Path("temp/queries/climate_anxiety_combined")
first_batch_dir = base_dir / "batch_1" / "review"
second_batch_dir = base_dir / "batch_2" / "review"
combined_dir = base_dir / "review"
combined_dir.mkdir(parents=True, exist_ok=True)

first_rows = json.loads((first_batch_dir / "review_table.json").read_text(encoding="utf-8"))
second_rows = json.loads((second_batch_dir / "review_table.json").read_text(encoding="utf-8"))

combined_rows = first_rows + second_rows
combined_rows = sorted(
    combined_rows,
    key=lambda row: (-int(row["score"]), row["paper_id"]),
)

export_review_tables(combined_rows, combined_dir, basename="review_table")
```

This produces a single review table that contains both batches, so you can review them together in one place.

---

## 10. Full example: generate one review table

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
