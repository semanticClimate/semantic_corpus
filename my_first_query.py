from pathlib import Path
from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

result = run_query_and_build_review_table(
    query_name="polluted_natural_resources_south_america",
    query_string='("pollution" AND "natural resources" AND "south america")',
    output_dir=Path("temp/queries/polluted_natural_resources_southamerica"),
    repository="europe_pmc",
    limit=10,
    formats=["xml", "pdf", "html"],
)

print(result["summary"])
print(result["review_paths"])