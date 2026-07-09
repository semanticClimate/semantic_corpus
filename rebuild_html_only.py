import json
from pathlib import Path

review_path = Path("temp/queries/climate_anxiety_2026/review/review_table.json")
rows = json.loads(review_path.read_text())

# Reuse the existing html_viewer module to build HTML from these exact rows
from semantic_corpus.corpus_review.review_table import export_review_tables

export_review_tables(rows, review_path.parent)
print("Rebuilt HTML/CSV/MD from current JSON, without touching JSON itself")
