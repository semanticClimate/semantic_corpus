from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

result = run_query_and_build_review_table(
    query_name="american_reports",
    query_string='("agrochemicals")',
    output_dir=Path("temp/queries/scielo_quey"),
    repository="scielo",
    limit=10,
    formats=["xml", "pdf", "html"],
)

print(result["summary"])
print(result["review_paths"])