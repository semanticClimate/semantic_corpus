# UK KG poster 2026 — companion page

**Poster:** Rapid scoping of climate literature with `semantic_corpus` (encyclopaedia + knowledge graphs)  
**Audience:** researchers, students, librarians, citizen scientists  
**This page:** documents the poster panels and gives **actionable** links and commands.

---

## Scan / QR

Encode **this page** (not the repo root) in the poster QR:

```text
https://github.com/semanticClimate/semantic_corpus/blob/pmr202610/docs/uk_kg_poster_2026.md
```

| Asset | Path |
|-------|------|
| Landing page (you are here) | [`docs/uk_kg_poster_2026.md`](uk_kg_poster_2026.md) |
| QR image (print-ready) | [`docs/uk_kg_poster_2026_qr.png`](uk_kg_poster_2026_qr.png) |
| Workflow strip (SVG) | [`docs/diagrams/poster_workflow.svg`](diagrams/poster_workflow.svg) |
| Workflow strip (PNG) | [`docs/diagrams/poster_workflow.png`](diagrams/poster_workflow.png) |

**Poster caption under QR:** `Scan: docs & try-me`

Regenerate the PNG after URL changes:

```bash
pip install 'qrcode[pil]'
python -c "import qrcode; qrcode.make(
  'https://github.com/semanticClimate/semantic_corpus/blob/pmr202610/docs/uk_kg_poster_2026.md'
).save('docs/uk_kg_poster_2026_qr.png')"
```

---

## What the poster claims (one screen)

`semantic_corpus` turns an open-literature **query** into a reusable **BagIt corpus**, then into **terms**, an interactive **paper↔term knowledge graph**, and optional **Wikipedia / Wikidata** annotation — transparent and reproducible (rule-based extraction + open metadata, not a black-box LLM).

**Project:** [github.com/semanticClimate/semantic_corpus](https://github.com/semanticClimate/semantic_corpus)  
**Community:** [semanticClimate](https://github.com/semanticClimate)

---

## Workflow (matches the poster strip)

Six stages — same spine as [`poster_workflow.svg`](diagrams/poster_workflow.svg):

| # | Poster label | What happens | Pipeline target |
|---|--------------|--------------|-----------------|
| 1 | **Collect** | Search open repositories (e.g. Europe PMC); fetch metadata + full text where available | `search` → `collect` |
| 2 | **Corpus** | BagIt bag; papers as packets under `data/packets/` | `corpus` |
| 3 | **Phrases** | Extract keyphrases / terms from packet text | `phrases` |
| 4 | **Bipartite** | Term ↔ packet (paper) incidence | inside `clusters` |
| 5 | **Clusters** | Communities + interactive **KG₁** (`--kg`) | `clusters --kg` |
| 6 | **Annotate** | Wikipedia / Wikidata on retained terms → **KG₂** | `encyclopedia --kg` |

Optional later: curate false positives (`clean`), lazy PDFs (`pdfs`), static reference docs (`--source`, e.g. IPCC HTML — design in [`ar6_html_ingest_design.md`](ar6_html_ingest_design.md)).

```text
query ──► collect ──► corpus ──► phrases ──► clusters [--kg→KG₁]
                                              │
                                              ▼
                                            clean
                                              │
                                              ▼
                                        encyclopedia [--kg→KG₂]
```

Full map: [`pipeline.md`](pipeline.md) · mappers: [`pipeline_kg_mappers.md`](pipeline_kg_mappers.md)

---

## Try this (actionable)

### 0. Setup (once)

```bash
git clone https://github.com/semanticClimate/semantic_corpus.git
cd semantic_corpus
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -e '.[cluster_review]'
```

### 1. Mini demo — query → interactive KG (~minutes)

```bash
./venv/bin/pipeline \
  --workdir corpora/amoc_30 \
  --query "AMOC" \
  --limit 30 \
  --target clusters \
  --kg
```

Open `corpora/amoc_30/kg/knowledge_graph.html` (orange = papers, blue = terms).

Step-by-step: [`tutorials/kg_from_query.md`](tutorials/kg_from_query.md)

### 2. Continue — encyclopaedia + annotated KG

```bash
./venv/bin/pipeline --workdir corpora/amoc_30 --target encyclopedia --kg
```

### 3. Resume / interrupt-safe collect

Collect writes packets as it goes; Ctrl-C keeps progress. Re-run the same command to resume.

[`tutorials/pipeline_epmc_resume.md`](tutorials/pipeline_epmc_resume.md) · lazy PDFs: [`tutorials/lazy_pdfs.md`](tutorials/lazy_pdfs.md)

### 4. Inspect without fetching

```bash
./venv/bin/pipeline list
./venv/bin/pipeline graph --from collect
./venv/bin/pipeline status --workdir corpora/amoc_30
```

---

## Poster panel cheat-sheet (for authors)

Use these headings on the printed poster so they match this page:

| Poster panel | Content on this page |
|--------------|----------------------|
| Title / subtitle | § What the poster claims |
| QR | § Scan / QR |
| Workflow strip | § Workflow + SVG/PNG assets |
| Why it matters | Open corpora → transparent graphs → citable evidence (RAG-ready bags) |
| Example | § Try this §1 (`AMOC`, limit 30) |
| Availability | This repo + tutorials below |
| Further reading | § Links |

**Suggested example queries** (same spirit as earlier AUKGET cases): `AMOC`, `ENSO AND SST`, `climate justice`, `Indian Ocean Dipole`.

---

## Links (docs & objects)

| Object | Link |
|--------|------|
| Pipeline overview | [`pipeline.md`](pipeline.md) |
| Worked examples | [`pipeline_examples.md`](pipeline_examples.md) |
| Tutorial: KG from query | [`tutorials/kg_from_query.md`](tutorials/kg_from_query.md) |
| Tutorial: resume collect | [`tutorials/pipeline_epmc_resume.md`](tutorials/pipeline_epmc_resume.md) |
| Tutorial: lazy PDFs | [`tutorials/lazy_pdfs.md`](tutorials/lazy_pdfs.md) |
| BagIt layout | [`bagit_structure.md`](bagit_structure.md) |
| AR6 HTML ingest (design) | [`ar6_html_ingest_design.md`](ar6_html_ingest_design.md) |
| README / install | [`../README.md`](../README.md) |
| Repository | https://github.com/semanticClimate/semantic_corpus |

---

## Cite / credit

- **Software:** semanticClimate / `semantic_corpus` — https://github.com/semanticClimate/semantic_corpus  
- **Community:** semanticClimate  
- **Poster companion:** `docs/uk_kg_poster_2026.md` (this file)

Update author list on the printed poster as needed; keep this page URL stable for the QR.
