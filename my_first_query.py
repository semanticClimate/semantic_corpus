from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

result = run_query_and_build_review_table(
    query_name="argentine_reports",
    query_string='("agrochemicals")', #clean query in conicet.py
    output_dir=Path("temp/queries/conicet_query"),
    repository="conicet",
    limit=10,
    formats=["pdf"], #no xml available in CONICET. The HTML will be automatically generated
)

print(result["summary"])
print(result["review_paths"])