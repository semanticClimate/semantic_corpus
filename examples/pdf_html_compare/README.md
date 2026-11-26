# Example — compare PDF, converted HTML, and original HTML

**Paper:** Marchi et al. (2020) *ClimateEU…* · Scientific Data · [PMC7719169](https://pmc.ncbi.nlm.nih.gov/articles/PMC7719169/) · CC-BY-4.0  

Open **[`compare.html`](compare.html)** in a browser (local file is fine). You should see three panes:

| Pane | What you see |
|------|----------------|
| **1. PDF input** | Published OA PDF (`tests/resources/input_adapters/oa_pdf_html_pair/`) |
| **2. Output HTML from PDF** | `output_from_pdf.html` — **legacy** extractor → sectioner → `indexed_text` |
| **3. Original HTML** | PMC full-text HTML (ground truth) |

Core scholarly wording should largely match; layout chrome and ads may differ.

## Pipeline (middle pane)

Built by [`semantic_corpus.corpus.legacy`](../../semantic_corpus/corpus/legacy/):

1. **Extractor** — `pymupdf` (baseline soft line-join), `docling` (structured HTML), or `amilib` (scholarly positioned HTML; optional).
2. **Sectioner** — mints `text_block` ids (`data-tb-kind`); optional **amilib** `PageJoiner` refine when sibling `amilib/scripts` is present and HTML has positioned divs.
3. **Output** — indexed HTML (+ `output_from_pdf.indexed.json` summary).

Marker / MinerU names are reserved stubs (not wired yet).

**amilib role:** owns line-join refinement, font-role / page-join paths, and richer scholarly HTML; wrap Docling (or future Marker/MinerU) as extractors, then refine + id-mint into `indexed_text`. Install: `pip install -e ../amilib` or `pip install 'semantic_corpus[legacy]'`.

## Regenerate the middle pane

```bash
# Default: pymupdf baseline with soft line-join + sectioner ids (fast)
python examples/pdf_html_compare/build_compare.py

# Docling (heavier; better tables/figures/lists)
python examples/pdf_html_compare/build_compare.py --engine docling

# amilib extract + refine (needs amilib + pdfplumber; sibling scripts for PageJoiner)
python examples/pdf_html_compare/build_compare.py --engine amilib --refine amilib
```

## Related

- API: [`semantic_corpus/corpus/legacy/`](../../semantic_corpus/corpus/legacy/)
- Fixture + overlap tests: [`tests/resources/input_adapters/oa_pdf_html_pair/`](../../tests/resources/input_adapters/oa_pdf_html_pair/)
- Pipeline tests: [`tests/test_legacy_pipeline.py`](../../tests/test_legacy_pipeline.py)
- Design: [`semantic_corpus/corpus/docs/input_adapters.md`](../../semantic_corpus/corpus/docs/input_adapters.md) §8–9
