# Prompt archive — common input adapters

**Date:** 2026-11-23  
**Derived docs:** [semantic_corpus/corpus/docs/input_adapters.md](../semantic_corpus/corpus/docs/input_adapters.md)

## Prompt (verbatim)

Most submodules take an input stream of semantic indexed HTML documents.  Where the input is less structured and semantic they need a common stateless input adapter which converts common formats into this, perhaps in two or more stages. Inputs include:
* PDF->text (ignoring images but preserving coordinates)
* DOCx->HTML
* raw text without coordinates
* OCRed text with coordinates

Where input is not indexed we need to add IDs heuristically.
Have I ignored anything?

Propose an input adapter and suggest any Open libraries which provide some or all of the process.
