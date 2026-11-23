# Prompt archive — module I/O types and storage

**Date:** 2026-11-21  
**Derived docs:** [semantic_corpus/corpus/docs/types_io_storage.md](../semantic_corpus/corpus/docs/types_io_storage.md)

## Prompt (verbatim)

We need to assign types to the inputs and outputs of each module and create *.py converters and annotators. For example `raw_text` is converted into `semantic_text` (which contains `text_block`s  with IDs).
We also have to decide where the outputs are stored - a `corpus` or local filestore.
Please identify types for input and outputs and design storage options
