# Pygetpapers directory ingestion – tests and usage

**Date:** February 18, 2025 (system date)

## Purpose

These tests check that a **classic pygetpapers** output directory can be ingested into a semantic_corpus (BAGIT) so that:

- Each paper (PMC folder) becomes one corpus paper with normalized metadata.
- Fulltext XML (and PDF when present) are copied into the corpus.
- The corpus remains valid (metadata, list, search).

## Test data

Tests use the fixture:

**`../amilib/test/resources/pygetpapers/wildlife/`**

- Layout: one folder per article (e.g. `PMC12124168/`) with:
  - `eupmc_result.json` – Europe PMC metadata
  - `fulltext.xml` – fulltext XML
  - `fulltext.pdf` – optional (wildlife fixture has XML + JSON; PDF may be present in other runs)
- The amilib repo must be a **sibling** of the semantic_corpus repo so that `../amilib/...` resolves. If the path is missing, ingestion tests are **skipped** (they do not fail).

## What the tests do

| Test | What it checks |
|------|----------------|
| **test_ingest_wildlife_adds_all_papers** | Ingest wildlife dir → number of papers added matches number of PMC folders; `list_papers()` returns the same IDs. |
| **test_ingest_wildlife_metadata_and_xml_present** | For a known paper (`europe_pmc_PMC12124168`): metadata has title, abstract, DOI; `data/documents/xml/{id}.xml` exists and is non-empty. |
| **test_ingest_wildlife_search_after_ingest** | After ingest, search by title (“wildlife”) and by abstract (“conservation”) returns at least one paper. |
| **test_ingest_nonexistent_dir_raises** | Ingest a non-existent path → `CorpusError` with a clear message. |
| **test_ingest_requires_bagit** | Ingest into a non-BAGIT corpus → `CorpusError` stating BAGIT is required. |
| **test_discover_paper_folders_wildlife** | Helper `_discover_paper_folders()` finds all PMC* folders with `eupmc_result.json` in the wildlife dir. |
| **test_eupmc_json_to_raw_metadata** | Helper `_eupmc_json_to_raw_metadata()` maps Europe PMC JSON (title, abstractText, authorString, etc.) to the raw dict used for normalization. |

## Running the tests

From the semantic_corpus repo root:

```bash
# All pygetpapers ingestion tests
python -m pytest tests/test_pygetpapers_ingestion.py -v

# Single test
python -m pytest tests/test_pygetpapers_ingestion.py::TestPygetpapersIngestion::test_ingest_wildlife_adds_all_papers -v
```

If the wildlife directory is not present (e.g. amilib not cloned or path different), pytest will **skip** the tests that depend on it and report something like:  
`SKIPPED (Pygetpapers wildlife fixture not found: ...)`.

## Using the ingester in code

```python
from pathlib import Path
from semantic_corpus.core.corpus_manager import CorpusManager
from semantic_corpus.ingestion.pygetpapers_ingester import ingest_pygetpapers_directory

corpus_dir = Path("corpora", "from_pygetpapers")
corpus = CorpusManager(corpus_dir, use_bagit=True)
corpus.create_structured_directories()

pygetpapers_dir = Path("../amilib/test/resources/pygetpapers/wildlife")
added = ingest_pygetpapers_directory(pygetpapers_dir, corpus)
# added is e.g. ["europe_pmc_PMC12124168", "europe_pmc_PMC12108416", ...]
```

Paper IDs in the corpus use the prefix `europe_pmc_` by default (e.g. `europe_pmc_PMC12124168`). Metadata is normalized via `MetadataProcessor`; XML (and PDF if present) are copied into `data/documents/xml/` and `data/documents/pdf/`.
