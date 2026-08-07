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