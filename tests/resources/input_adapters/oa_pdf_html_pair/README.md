# OA PDF + HTML pair — ClimateEU (PMC7719169)

**Purpose:** Extended extractor/sectioner test: published academic **PDF as input**, OA **HTML as ground truth** for shared core scholarly text.

| File | Role |
|------|------|
| `ClimateEU_PMC7719169.pdf` | Extractor input (9 pp; Nature/Scientific Data PDF) |
| `ClimateEU_PMC7719169.html` | Ground truth (PMC full-text HTML) |
| `ClimateEU_PMC7719169.jats.xml` | Optional structured OA full text (Europe PMC) |
| `manifest.json` | Citation, license, core phrases for overlap checks |

## Citation

Marchi et al. (2020). *ClimateEU, scale-free climate normals, historical time series, and future projections for Europe.* Scientific Data 7:428.  
DOI: [10.1038/s41597-020-00763-0](https://doi.org/10.1038/s41597-020-00763-0) · PMCID: [PMC7719169](https://pmc.ncbi.nlm.nih.gov/articles/PMC7719169/) · License: **CC-BY-4.0**

## Reader-facing comparison

Open **[`examples/pdf_html_compare/compare.html`](../../../../examples/pdf_html_compare/compare.html)** in a browser for three panes: **PDF**, **HTML from PDF**, **original PMC HTML**.

## Expectations

- Core scholarly prose is shared; PDF↔HTML may each include **adverts, chrome, or editorial** the other lacks.
- Compare with **whitespace-normalized** phrase overlap; tolerate false negatives (sample-literature stance).
- Page coordinates are optional and not required for this test.

## Regeneration

```bash
curl -sL -o ClimateEU_PMC7719169.pdf \
  "https://www.nature.com/articles/s41597-020-00763-0.pdf"
curl -sL -o ClimateEU_PMC7719169.html \
  "https://pmc.ncbi.nlm.nih.gov/articles/PMC7719169/"
curl -sL -o ClimateEU_PMC7719169.jats.xml \
  "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7719169/fullTextXML"
```
