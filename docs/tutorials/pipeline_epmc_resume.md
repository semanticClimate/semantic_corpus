# Tutorial: EPMC corpus with interruptible collect + lazy PDFs

Build a portable BagIt corpus from Europe PMC, stop mid-download, resume, then
optionally fetch PDFs later. PDFs are **not** required for phrases / clusters /
encyclopedia and should stay out of GitHub (`corpora/**/*.pdf` is gitignored).

**Layout:** [bagit_structure.md](../bagit_structure.md) · **CLI:** [pipeline.md](../pipeline.md)

## Prerequisites

```bash
pip install -e '.[cluster_review,test]'
# optional: Docling for PDF → XML when publisher XML is missing
```

## 1. Search + collect (JSON + XML only)

```bash
pipeline --workdir corpora/demo_amoc_50 \
  --query "AMOC AND insolation" --limit 50 \
  --repository europe_pmc \
  --target collect
```

What this does:

1. **`search`** — writes `query.json`, `search_results.json`, light `bagit.txt`
2. **`collect`** — for each hit, writes under `data/packets/`:
   - `PMC….json` (metadata / abstract)
   - `PMC….xml` when EPMC fullTextXML works  
   PDFs are **not** downloaded here.

Interrupt with Ctrl-C at any time. Files already written stay on disk.

## 2. Resume after a break

Same command again (or omit `--query` if `search_results.json` already exists):

```bash
pipeline --workdir corpora/demo_amoc_50 \
  --query "AMOC AND insolation" --limit 50 \
  --target collect
```

- Papers with valid `PMC….json` **and** XML (`PMC….xml` or later `PMC….pdf.xml`) are **skipped**
- Abstract-only is **not** treated as finished — collect retries XML
- If XML is definitively unavailable, `{id}.json` gets `"_collect_xml": "unavailable"` so resume does not loop forever

Check progress:

```bash
ls corpora/demo_amoc_50/data/packets/*.xml | wc -l
pipeline --workdir corpora/demo_amoc_50 status --target collect
```

## 3. Phrases → clusters → encyclopedia (no PDFs needed)

```bash
pipeline --workdir corpora/demo_amoc_50 \
  --phrase-method tfidf --phrase-n 3 --phrase-top 15 \
  --cluster-resolution 0.8 \
  --target encyclopedia
```

Start mode is **`existing`** when you omit `--query` (uses the bag under `--workdir`).

Artifacts (BagIt reduce tree):

```text
corpora/demo_amoc_50/
  search_results.json
  data/packets/PMC….json|.xml
  data/indexes/packets.json
  data/indexes/phrases/
  data/indexes/clusters/
  encyclopedia/          # annotate outputs (corpus-bound)
  pipeline/*.stamp
```

## 4. Lazy PDFs (bulk)

Fill missing PDFs for the whole hit list:

```bash
pipeline --workdir corpora/demo_amoc_50 --target pdfs
```

- Skips papers that already have a valid `data/packets/PMC….pdf`
- If publisher XML is still missing, may run Docling → `PMC….pdf.xml`

## 5. Lazy PDF (one paper)

```bash
pipeline --workdir corpora/demo_amoc_50 \
  --paper-id PMC11864975 \
  --target pdfs
```

Useful from a review UI or when one paper is interesting for figures / reading.

## 6. Suggested workflow for large limits (e.g. 1000)

```bash
# Night 1 — search + as much XML as you can
pipeline --workdir corpora/amoc_1000 \
  --query "AMOC" --limit 1000 --target collect
# … interrupt after ~200 …

# Later — resume XML
pipeline --workdir corpora/amoc_1000 \
  --query "AMOC" --limit 1000 --target collect

# Indexing / KG without waiting on PDFs
pipeline --workdir corpora/amoc_1000 --target clusters --kg

# Optional — PDFs when bandwidth allows
pipeline --workdir corpora/amoc_1000 --target pdfs
```

## Notes

| Topic | Behaviour |
|-------|-----------|
| GitHub | Do not commit `corpora/**/*.pdf` |
| Text cascade | `.xml` → `.pdf.xml` → abstract in `.json` |
| Other repos | `--repository` selects an adapter; EPMC is the primary path |
| `--source` | Static document ingest still placeholder |
