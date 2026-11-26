# Prompt archive — `indexed_text` intermediate specification

**Date:** 2026-11-26  
**Derived docs:** [semantic_corpus/corpus/docs/indexed_text.md](../semantic_corpus/corpus/docs/indexed_text.md)

## Prompt (verbatim)

`repositories` (extractor) creates an output of documents (content and metadata) which is then sectioned and indexed (text_blocks+ids and metadata). This is later fed into phrase_kg and (separately) chatbot. Please create a specification for this intermediate.

## Discussion

- Named the intermediate **`indexed_text`** (synonym of older `semantic_text` / `SemanticDocument` for the consumer contract).
- Clarified pipeline: `repositories` → **document** (content + metadata) → sectioner/indexer → **`indexed_text`** → `phrases_kg` | `chatbot` (independent).
- Spec covers required fields, `text_block` shape, metadata/provenance, JSON sketch, consumer contracts, invariants, non-goals.
- Cross-links: types catalog, siblings, input_adapters, chatbot export migration note.
