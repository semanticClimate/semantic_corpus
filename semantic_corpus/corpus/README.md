# Module `corpus` — ingest and BagIt

**Status:** primary (JOSS focus for this repository)  
**Owner:** Renu Kumari  
**Spec:** [`MODULE_SPEC.md`](../MODULE_SPEC.md) · **Docs:** [`docs/modules/corpus/overview.md`](../../docs/modules/corpus/overview.md)

## Role

Personal corpus create → search/download → ingest → BagIt (+ review table as QA).

## Facilities

See `module.yaml` (`corpus_manager`, `ingest`, `bagit`, `review_qa`, `epmc`).

## Public imports

```python
from semantic_corpus.corpus import MODULE_NAME, load_meta
from semantic_corpus.core.corpus_manager import CorpusManager  # legacy path until fully moved
```

Implementation still lives mainly under `core/`, `ingestion/`, `storage/`, and `corpus_review/`; this package is the normalised module face.
