# Tutorial: Lazy PDF download

PDFs are large, often gitignored, and optional for indexing. Use them when you need
figures or a human-readable original, or when Docling must derive XML from PDF.

See also: [pipeline_epmc_resume.md](pipeline_epmc_resume.md) · [bagit_structure.md](../bagit_structure.md)

## Why lazy?

| Goal | Artifact |
|------|----------|
| Phrases / clusters / encyclopedia | `data/packets/{id}.xml` or `{id}.pdf.xml` / abstract JSON |
| Read paper + figures | `{id}.pdf` on demand |
| Low-bandwidth clone | Indexed corpus without PDFs |

`collect` never requires PDFs. `pdfs` fills them later.

## Bulk fill

```bash
pipeline --workdir corpora/demo_amoc_50 --target pdfs
```

Writes `data/packets/PMC….pdf` only when missing. Existing valid PDFs are skipped.

## One paper (download button)

```bash
pipeline --workdir corpora/demo_amoc_50 \
  --paper-id PMC12345678 \
  --target pdfs
```

Wire a UI “Download PDF” control to this command (or call `run_pdfs` / `run_paper(..., formats=["pdf"])` from Python).

## After PDF: derived XML

If publisher XML was unavailable, the `pdfs` step may create `PMC….pdf.xml` via Docling
so phrase extraction can use full text without keeping the PDF in git.

## Check

```bash
ls corpora/demo_amoc_50/data/packets/*.pdf | head
pipeline --workdir corpora/demo_amoc_50 status --target pdfs
```
