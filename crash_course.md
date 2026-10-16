# Crash course

All commands run from the repo root (PowerShell).

## A. Download papers

1. Search, download, convert PDFs and build the review table:
    (First, edit the query values in `my_first_query.py` to fit your needs.)
   ```powershell
   .\.venv\Scripts\python.exe my_first_query.py
   ```
   Output: `temp\queries\test_query\review\` (`.json`, `.html`, `.csv`, `.md`).
2. (Optional) Rebuild the table without downloading again:
   ```powershell
   .\.venv\Scripts\python.exe scripts\build_review_table.py --query-dir temp\queries\test_query
   ```
3. Serve the viewer at http://127.0.0.1:8765/review_table.html:
   ```powershell
   .\.venv\Scripts\python.exe scripts\review_viewer.py serve --review-table temp\queries\test_query\review\review_table.json --query-dir temp\queries\test_query
   ```

If you change `query_name` / `output_dir` in `my_first_query.py`, replace `test_query` above.

## B. Use local PDFs

1. Import PDFs into a corpus and convert them to HTML/XML (Docling):
   ```powershell
   .\.venv\Scripts\python.exe -m semantic_corpus.cli import --pdf-dir "your_path" --name my_corpus --recursive --convert
   ```
   Already-imported PDFs are skipped and not reconverted. To reconvert:
   ```powershell
   .\.venv\Scripts\python.exe -m semantic_corpus.cli convert --corpus temp\corpus\my_corpus --overwrite
   ```
2. Build the table in `temp\corpus\my_corpus\review\`:
   ```powershell
   .\.venv\Scripts\python.exe scripts\build_review_table.py --corpus temp\corpus\my_corpus
   ```
3. Serve the viewer at http://127.0.0.1:8765/review_table.html:
   ```powershell
   .\.venv\Scripts\python.exe scripts\review_viewer.py serve --review-table temp\corpus\my_corpus\review\review_table.json --corpus-dir temp\corpus\my_corpus
   ```

Stop the server with `Ctrl+C`.

## Linter and formatter (Ruff)

Run before committing:
```powershell
.\.venv\Scripts\python.exe -m ruff check --fix .
.\.venv\Scripts\python.exe -m ruff format .
```

Check only, as CI does:
```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

If Ruff is missing: `.\.venv\Scripts\python.exe -m pip install ruff`
