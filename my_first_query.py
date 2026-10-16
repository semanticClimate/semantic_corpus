from pathlib import Path

from semantic_corpus.corpus_review.workflow import run_query_and_build_review_table

result = run_query_and_build_review_table(
    query_name="test_query",
    query_string='("climate anxiety")',  # clean query in conicet.py
    output_dir=Path("temp/queries/test_query"),
    repository="europe_pmc",
    limit=10,
    formats=[
        "pdf",
        "xml",
    ],  # no xml available in CONICET or UBA servers; convert_pdfs generates XML/HTML via Docling
    convert_pdfs=True,
)

print(result["summary"])
print(result["review_paths"])
