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

# =====================================================================
# OPCION A: DESCARGAR papers (Europe PMC, etc.)
# =====================================================================
# 1. Buscar, descargar, convertir PDFs y armar la tabla (este archivo):
#    .\.venv\Scripts\python.exe my_first_query.py
#    -> genera temp\queries\test_query\review\review_table.json (.html, .csv, .md)
#
# 2. (Opcional) Regenerar la tabla sin volver a descargar:
#    .\.venv\Scripts\python.exe scripts\build_review_table.py --query-dir temp\queries\test_query
#
# 3. Abrir el visor en localhost (http://127.0.0.1:8765/review_table.html):
#    .\.venv\Scripts\python.exe scripts\review_viewer.py serve --review-table temp\queries\test_query\review\review_table.json --query-dir temp\queries\test_query
#
# (Si cambias query_name / output_dir arriba, cambia "test_query" en los comandos.)

# =====================================================================
# OPCION B: usar PDFs que ya tenes en tu compu
# =====================================================================
# 1. Importar los PDFs al corpus y convertirlos a HTML/XML con Docling:
#    .\.venv\Scripts\python.exe -m semantic_corpus.cli import --pdf-dir "your_path" --name my_corpus --recursive --convert
#    (si los PDFs ya estaban importados, los saltea y NO los reconvierte; para reconvertir:
#     .\.venv\Scripts\python.exe -m semantic_corpus.cli convert --corpus temp\corpus\my_corpus --overwrite)
#
# 2. Armar la tabla en temp\corpus\my_corpus\review\ (.json, .html, .csv, .md):
#    .\.venv\Scripts\python.exe scripts\build_review_table.py --corpus temp\corpus\my_corpus
#
# 3. Abrir el visor en localhost (http://127.0.0.1:8765/review_table.html):
#    .\.venv\Scripts\python.exe scripts\review_viewer.py serve --review-table temp\corpus\my_corpus\review\review_table.json --corpus-dir temp\corpus\my_corpus
#
# Para frenar el servidor: Ctrl+C
