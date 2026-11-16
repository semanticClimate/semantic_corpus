# Module 2 — Global South harvesting

**Logical module:** `global_south`  
**JOSS focus:** separate paper theme; code stays **in this repo**  
**Owner focus:** Larisa Beni  
**Co-authors (all papers):** Renu Kumari, Peter Murray-Rust  

---

## Purpose

Harvest scholarly literature from **Global South and non-EN-centric** open sources into the **same corpus contracts** as Module 1 (IDs, documents, review rows, BagIt/flat layout)—without forking a second corpus product.

---

## In scope

- Repository adapters under `semantic_corpus/repositories/`:  
  - **SciELO**, **Redalyc**, **CONICET**  
  - Latin American university / IR scrapers (e.g. UBA, USP, UNAL, UNAM, UChile, Kerwa, …)  
  - Shared scraping helpers (`_scraper.py`) where used  
- Non-English metadata and full-text quirks (encoding, landing pages, PDF-only)  
- Tests for adapters (real fixtures or `SC_LIVE_API=1`; **no mocks**)  
- Tutorials that show GS sources feeding the **same** review/BagIt path as EPMC  

---

## Out of scope

| Belongs elsewhere | Module |
|-------------------|--------|
| BagIt packing, EPMC-first CLI story | [ingest_bagit.md](ingest_bagit.md) |
| Phrase/KG science on top of bags | [phrases_kg.md](phrases_kg.md) |
| Topic PDF reading piles | Not software — do not commit (`agrochemicals/` removed) |

---

## Boundaries

- Adapters implement the **shared repository interface**; they must not invent a parallel corpus layout.  
- Prefer declarative config (YAML query pilots) for demos.  
- Optional install extra `[gs]` if heavy deps appear; default JOSS ingest install need not pull scraper stacks.  

---

## JOSS claim (draft one-liner)

Open adapters bring SciELO, Redalyc, CONICET and related Global South sources into the same personal-corpus / BagIt workflow used for Europe PMC.
