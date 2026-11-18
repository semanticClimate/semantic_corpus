# Uniqueness and related systems

**Date:** 2026-11-16  
**Status:** positioning note for papers / proposals  
**Audience:** authors arguing what `semantic_corpus` (and the AMI / semanticClimate lineage) contribute  
**Related:** [pipeline.md](pipeline.md) · [pipeline_kg_mappers.md](pipeline_kg_mappers.md) · [ar6_html_ingest_design.md](ar6_html_ingest_design.md) · [bagit_structure.md](bagit_structure.md)

---

## 1. What we are justifying

We process **trusted** scholarly papers and institutional documents (NGO / government / IPCC-like reports) into **small, well-defined semantic components** with **stable unique IDs**, then use those components for phrases, graphs, encyclopaedia annotation, and human review.

Two product strategies:

| Strategy | Meaning |
|----------|---------|
| **(a) Small rapid-scoping corpus** | Minutes-to-hours local corpus from a query or fixed inventory — not a mega-catalogue |
| **(b) Flexible trusted input** | Not journal PDFs only: OA articles **and** normative / web / report HTML (and PDF when needed) |

**Claim style:** (a) and (b) are **design requirements**, not uniqueness proofs by themselves. Uniqueness is argued from the **combination** of (a)+(b) with our **indexing doctrine** and **end-to-end local pipeline**.

---

## 2. Problem layers

```text
1. Intake     trusted OA papers + NGO/gov/report docs
2. Semantics  packets / sections / paras with stable IDs + types
3. Use        phrases, term↔packet KG, Wikipedia annotate, review, later RAG
```

`semantic_corpus` today is strong on **intake (OA)** and **use (phrases / KG / encyclopaedia)**. Fine-grained packetization is **designed** ([pipeline_kg_mappers.md](pipeline_kg_mappers.md)); EPMC path often still uses a whole-document body packet. IPCC-style HTML-with-IDs lives mainly in the AMI / `amilib` lineage, with declarative AR6 ingest designed in [ar6_html_ingest_design.md](ar6_html_ingest_design.md).

---

## 3. Related systems (summary)

### 3.1 Structure extractors (tool layer)

| System | Role | Corpus? |
|--------|------|---------|
| **GROBID** | PDF → TEI; scholarly structure, refs | **Tool** (ships small training sets, not a research corpus product) |
| **CERMINE** | PDF → JATS | Tool |
| **Docling**, Marker, MinerU, Nougat, LlamaParse, Unstructured | General PDF/HTML → MD/JSON/HTML | Tools (often RAG-oriented) |
| **Trafilatura / Readability** | Web main-content HTML | Tools |

**GROBID** is a component we already treat as such — not a competitor corpus. It is optimised for **academic articles**, not IPCC/SPM/annex layouts.

### 3.2 Large scholarly corpora / graphs

| System | Role |
|--------|------|
| **S2ORC** | Full-text scholarly corpus; now a Semantic Scholar **bulk dataset** (API), continuously rebuilt in principle (check latest release id; cadence can stall) |
| **S2AG / Semantic Scholar** | Huge bibliographic KG (papers, authors, citations, embeddings) |
| **OpenAlex, CORE, Europe PMC, Crossref** | Metadata / OA aggregation and APIs |
| **PubGraph** etc. | Catalogue-scale science KGs |

These own **scale** and **biblio semantics**. They rarely deliver **personal BagIt corpora** or **paragraph-level IDs for normative reports**.

### 3.3 Client-side / AMI lineage (closest ancestors)

| System | Role |
|--------|------|
| **ContentMine AMI + Norma** | CProject / `scholarly.html`; dictionary/regex fact plugins |
| **pyami / pyamihtml / amilib / amiclimate** | PDF/HTML → semantic HTML; IPCC chapters with section/para IDs |
| **#semanticClimate** | Climate semantic HTML + Wikidata-oriented terms |
| **pygetpapers** | Query → download folders (intake only) |

### 3.4 Rapid review / personal libraries

Zotero, Covidence, Rayyan, and similar support **small collections** and screening. They do not generally own structural packet IDs + term–packet KG + BagIt semantic pipeline.

### 3.5 RAG chunkers

Unstructured / LlamaParse / generic “semantic chunking” invent **query- or embedding-oriented spans**. That conflicts with our rule: **index from document structure first; mappers only match/annotate**.

---

## 4. Overlap (what we do not claim as unique alone)

| Capability | Also seen in |
|------------|----------------|
| OA search + download | pygetpapers, EPMC/CORE clients, ContentMine-era scrapers |
| Prefer publisher XML when available | JATS/PMC pipelines; CERMINE spirit |
| PDF → structured text | GROBID, Docling, Marker, … |
| Keyphrases / term graphs | Classical IR; domain KGs on OpenAlex abstracts |
| Wikipedia / Wikidata linking | Linked-data enrichment generally |
| Small query-driven sets | Review tools, Zotero, pygetpapers |
| General (non-article) PDFs | Docling, Unstructured, Trafilatura |

---

## 5. Where uniqueness lies

### 5.1 Not unique in isolation

| Strategy | Verdict | Safer wording |
|----------|---------|----------------|
| **(a) Small rapid scoping** | Common as a *practice* | Personal/group **rapid-scoping corpora** with skip-if-done BagIt pipelines |
| **(b) Not just academic** | Common among *general* parsers | **Heterogeneous trusted sources** (OA articles + institutional reports) under one packet/KG model |

### 5.2 Distinctive combination (use this)

Few systems combine all of:

1. **Rapid local scoping** — small corpora in minutes/hours, user-owned disk, resume/skip-if-done  
2. **Heterogeneous trusted intake** — OA papers **and** NGO/gov/normative HTML (PDF as sidecar / Docling fallback), not “any PDF for RAG”  
3. **Index-before-map** — stable packet addresses from authoritative numbering → containment → sequence; mappers do not invent spans  
4. **Transparent enrichment** — phrases → bipartite term↔packet graph → optional Wikipedia annotate / FP curation (not LLM-first chunking)  
5. **Preservation-oriented packaging** — BagIt + checksums + provenance-friendly layout  
6. **AMI / report lineage** — path from ContentMine-style semantic HTML (e.g. IPCC `html_with_ids`) into the same corpus/KG machinery as EPMC papers  

**One-sentence claim for papers:**

> *semantic_corpus* provides a local, preservation-ready pipeline for **rapid scoping corpora** drawn from **trusted scholarly and institutional documents**, converting them into **structurally indexed semantic components** and **transparent term–packet knowledge graphs** — unlike mega biblio platforms (S2ORC/S2AG), article-only parsers (GROBID-as-product), or RAG chunkers that define spans at retrieval time.

### 5.3 Positioning relative to named systems

| System | Relationship |
|--------|----------------|
| **GROBID** | **Component / baseline** for hard PDFs; not our corpus product |
| **Docling** | **Component** (PDF → XML/HTML fallback); already wired optionally |
| **S2ORC / S2AG** | **Scale reference** for full-text scholarly parsing & biblio KGs; different goal (platform corpus vs personal bag) |
| **pygetpapers** | **Intake cousin**; we add BagIt, streams, resume, phrases/KG |
| **AMI / pyamihtml / amilib** | **Semantic HTML / ID ancestors**; declarative AR6 design continues that line |
| **Unstructured / LlamaParse** | Contrasting **RAG chunk** philosophy |

---

## 6. Implications for a paper series

| Paper wedge | Emphasise |
|-------------|-----------|
| Corpus architecture | BagIt + containers/packets + index-before-map vs RAG chunks vs S2ORC JSON |
| Intake | Multi-stream OA collect + resume; declarative report HTML packs |
| Normative documents | AR6 WG*/SYR HTML-with-IDs vs article-only IE |
| Semantics → graph | Term↔packet BKG + encyclopaedia vs citation/author KGs |
| Trust & provenance | Trusted sources + structural IDs + bag checksums for audit / grounded RAG |

**Do cite** GROBID, S2ORC, Docling, OpenAlex/EPMC as components, baselines, or supply chains.  
**Do not claim** uniqueness for “downloading papers” or “parsing PDF” alone.

---

## 7. Honest gaps (strengthens credibility)

- Fine-grained EPMC/JATS packetization is incomplete relative to the design.  
- NGO/gov declarative ingest is early (AR6 design; `--source` still maturing).  
- We are not trying to beat GROBID on every journal layout; we prefer born-digital XML/HTML.  
- Mega-platform coverage and embeddings are out of scope by choice.

---

## 8. Short abstract blurb (copy-ready)

Open tools already download papers, parse PDFs, and build enormous bibliographic graphs. What remains scarce is a **user-owned, preservation-ready** workflow for **rapid scoping** over **trusted heterogeneous documents** — scholarly articles together with institutional reports — that yields **small semantic components with stable IDs** and **transparent term–document graphs**. *semantic_corpus* (with the AMI / semanticClimate lineage) targets that niche: index structure first, map second; treat GROBID/Docling as components and S2ORC/S2AG as scale references, not substitutes for personal corpora of mixed trusted sources.
