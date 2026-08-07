## Build a Semantic Corpus from a Europe PMC Query

This tutorial demonstrates how to search Europe PMC, download open-access literature, generate a review table, and review the retrieved papers before building a semantic corpus.

### Step 1. Navigate to the repository

Open a Command Prompt and navigate to the `semantic_corpus` repository.

```bash
cd semantic_corpus
```

### Step 2. Create a query script

Create a new Python script.

```cmd
notepad create_query.py
```

Copy and paste the following code into `create_query.py`. 

```python
from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

result = run_query_and_build_review_table(
    query_name="medplant",
    query_string=(
        '(phytochemical* OR "plant secondary metabolites") '
        'AND ("medicinal plants" OR herbal OR ethnobotany)'
    ),
    output_dir=Path("temp/queries/medplant"),
    repository="europe_pmc",
    limit=20,
    formats=["xml", "pdf"],
)

print(result["summary"])
print(result["review_paths"])
```

> **Things to remember**
>
> Replace the values of `query_name`, `query_string`, `output_dir` and `limit` with your own research topic. 
>


### Step 3. Run the query

Execute the script.

```bash
python create_query.py
```

This workflow will:

- Search Europe PMC.
- Download available XML and PDF files.
- Generate a review table.
- Save all outputs under:

```text
temp/
└── queries/
    └── medplant/
        ├── query_run.json
        ├── search_results.json
        ├── xml/
        ├── pdf/
        └── review/
```

### Step 4. Launch the review interface

**Things to remember**
>
> Change the file path of `review-table` and `query-dir` according to your output dir.
> 

Start the interactive review server.

```bash
python scripts/review_viewer.py serve --review-table temp\queries\medplant\review\review_table.json --query-dir temp\queries\medplant
```

Open the URL displayed in the terminal (typically `http://127.0.0.1:8000`) in your web browser.

The review interface allows you to:

- Browse the retrieved publications.
- Read titles and abstracts.
- View downloaded XML and PDF files.
- Include or exclude papers.
- Save your review decisions.

After reviewing the literature, your curated corpus is ready for downstream semantic analysis using the semanticClimate toolkits.