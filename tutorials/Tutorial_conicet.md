Here's a short walkthrough to use the CONICET repo I've added. It is based on Vrinda's

1) Clone the repository

```bash
git clone https://github.com/semanticClimate/semantic_corpus.git
cd semantic_corpus
```


2) Check Python

```bash
python --version
```

If Python is not installed, install Python 3.10 or newer first.

3) Create a virtual environment

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


4) Install the package and dependencies

From the repository root, install the project:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

5) Create a folder for your first query

```bash
mkdir -p temp/queries/my_first_query
```

```text
temp/queries/my_first_query/
```

6) Put the query code in a Python file

For a first run, create a simple Python file in the repository root.

```text
semantic_corpus/my_first_query.py
```

Open that file in a text editor and paste in the following code:

```python
from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

result = run_query_and_build_review_table(
    query_name="argentine_reports",
    query_string='("agrochemicals")', 
    output_dir=Path("temp/queries/conicet_query"),
    repository="conicet",
    limit=10, #or as many as you wish
    formats=["pdf"], #no xml available in CONICET. The HTML will be automatically generated
)
```

Then run it from the terminal while you are inside the repository folder:

```bash
python my_first_query.py
```

7)   
- In order to generate the review_table.html: .\venv\Scripts\python.exe scripts/build_review_table.py --query-dir temp/queries/conicet_query
- In order to start the server: .\venv\Scripts\python.exe scripts/review_viewer.py serve --review-table temp/queries/conicet_query/review/review_table.json --query-dir temp/queries/conicet_query 

Either the website is automatically loaded or you run http://localhost:8765/review_table.html

There you can accept/discard the papers, make notes and save the results. 
