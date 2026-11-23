# Module `phrases_kg` — phrases and bipartite KGs

**Status:** extension  
**Owner:** Neel Kumar + Anusha  
**Spec:** [`MODULE_SPEC.md`](../MODULE_SPEC.md) · **Docs:** [`docs/modules/phrases_kg/overview.md`](../../docs/modules/phrases_kg/overview.md) · **Controls:** [`docs/modules/phrases_kg/controls.md`](../../docs/modules/phrases_kg/controls.md)

## Role

From a corpus **or** flat documents—optionally with a glossary (skip extraction)—extract term-phrases and build a bipartite term↔document_component graph, or a term↔term projection.

## Facilities

See `module.yaml` (`phrases`, `clusters`, `kg`, `packets`).

## Public imports

```python
from semantic_corpus.phrases_kg import MODULE_NAME, load_meta
from semantic_corpus.cluster_review.step2 import extract_phrases  # legacy path until fully moved
```

Implementation still lives mainly under `cluster_review/`; this package is the normalised module face.
