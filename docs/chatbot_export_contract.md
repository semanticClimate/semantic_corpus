# Chatbot export contract

**Date:** 2026-07-03 (system date)

## Purpose

Define the handoff from **semantic_corpus** (reviewed BAGIT corpus) to **../chatbot** RAG indexing.

## Manifest file

`chatbot_manifest.json` produced by `semantic_corpus.export.chatbot_export.export_corpus_for_chatbot`.

### Top-level fields

| Field | Description |
|-------|-------------|
| `export_version` | Contract version (currently `"1.0"`) |
| `corpus_dir` | Absolute path to source BAGIT corpus |
| `paper_count` | Number of papers in export |
| `papers` | List of paper source records |
| `chunking_hint` | Guidance for chatbot indexer |

### Per-paper record (`papers[]`)

| Field | Description |
|-------|-------------|
| `source_id` | Corpus paper ID (e.g. `europe_pmc_PMC12345`) |
| `citation_label` | Human-readable citation for UI |
| `title`, `abstract`, `doi`, `pmcid`, `pmid` | Metadata for retrieval and display |
| `publication_date`, `journal`, `authors` | Bibliographic fields |
| `xml_path` | Full path to fulltext XML if present |
| `pdf_path` | Full path to PDF if present |
| `metadata_path` | Path to normalized metadata JSON in corpus |

### Chunking hint

- **Primary text source:** `xml_path` (chunk fulltext for RAG).
- **Fallback:** `abstract` when XML missing.
- **Retrieval metadata:** title, abstract, doi, pmcid, citation_label.

## Chatbot indexer responsibilities

1. Read `chatbot_manifest.json`.
2. For each paper, load text from `xml_path` or `abstract`.
3. Chunk text (policy defined in chatbot; not in semantic_corpus).
4. Store chunks in vector index with metadata: `source_id`, `citation_label`, `doi`, `pmcid`, section anchors if parsed from XML.
5. At answer time, cite using `citation_label` and link to source identifiers.

## Selection filter

Only papers with `review_status == include` in the review table are exported when using `export_corpus_for_chatbot(..., include_only_status=True)`.

## Versioning

Increment `export_version` when breaking changes are made to manifest shape.
