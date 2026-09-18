from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

result = run_query_and_build_review_table(
    query_name="test_query",
    query_string='("clima")', #clean query in conicet.py
    output_dir=Path("temp/queries/test_query"),
    repository="conicet",
    limit=10,
    formats=["pdf", "xml"], #no xml available in CONICET. The HTML will be automatically generated
)

print(result["summary"])
print(result["review_paths"])

#.\venv\Scripts\python.exe scripts/review_viewer.py serve --review-table temp/queries/test_query/review/review_table.json --query-dir temp/queries/test_query
#.\venv\Scripts\python.exe scripts/build_review_table.py --query-dir temp/queries/test_query

#agy --conversation=c6875ad8-b7d8-4a57-b8f8-334d8ec0974d