# Module — Literature repositories

**Logical module:** `repositories`  
**Package:** `semantic_corpus.repositories`  
**JOSS focus:** separate paper theme; code stays **in this repo**  
**Owner focus:** Larisa Beni  
**Co-authors (all papers):** Renu Kumari, Peter Murray-Rust  
**Spec:** [`MODULE_SPEC.md`](../../../semantic_corpus/MODULE_SPEC.md) · **Metadata:** `semantic_corpus/repositories/module.yaml`

---

## Purpose

Harvest scholarly literature from **open repositories**—including **Global South and non-EN-centric** sources—into the **same corpus contracts** as the `corpus` module (IDs, documents, review rows, BagIt/flat layout)—without forking a second corpus product.

---

## In scope

- Repository adapters under `semantic_corpus/repositories/`:  
  - **Europe PMC**, **OpenAlex** (shared with the corpus primary path)  
  - **SciELO**, **Redalyc**, **CONICET**  
  - Latin American university / IR scrapers (e.g. UBA, USP, UNAL, UNAM, UChile, Kerwa, …)  
  - Shared scraping helpers (`_scraper.py`) and paper-ID helpers (`_ids.py`) where used  
- Non-English metadata and full-text quirks (encoding, landing pages, PDF-only)  
- Tests for adapters (real fixtures or `SC_LIVE_API=1`; **no mocks**)  
- Tutorials that show repository sources feeding the **same** review/BagIt path  

---

## Out of scope

| Belongs elsewhere | Module |
|-------------------|--------|
| BagIt packing, EPMC-first CLI story | [corpus](../corpus/overview.md) |
| Phrase/KG science on top of bags | [phrases_kg](../phrases_kg/overview.md) |
| Topic PDF reading piles | Not software — do not commit (`agrochemicals/` removed) |

---

## Boundaries

- Adapters implement the **shared repository interface**; they must not invent a parallel corpus layout.  
- Prefer declarative config (YAML query pilots) for demos.  
- Optional install extra `[repositories]` if heavy deps appear; default JOSS ingest install need not pull scraper stacks.  

---

## Docs

- South Asia sources / **possible Shodhganga** work: [south_asia.md](south_asia.md)

---

## JOSS claim (draft one-liner)

Open adapters bring SciELO, Redalyc, CONICET and related Global South sources into the same personal-corpus / BagIt workflow used for Europe PMC.
