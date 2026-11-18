# Module `phrases_kg` — phrases and bipartite KGs

**Status:** extension  
**Owner:** Neel Kumar  
**Spec:** [`MODULE_SPEC.md`](../MODULE_SPEC.md) · **Docs:** [`docs/modules/phrases_kg/overview.md`](../../docs/modules/phrases_kg/overview.md)

## Role

From an already ingested corpus, extract lightweight phrases, build bipartite paper↔term structure, and support transparent KG views.

## Facilities

See `module.yaml` (`phrases`, `clusters`, `kg`, `packets`).

## Public imports

```python
from semantic_corpus.phrases_kg import MODULE_NAME, load_meta
from semantic_corpus.cluster_review.step2 import extract_phrases  # legacy path until fully moved
```

Implementation still lives mainly under `cluster_review/`; this package is the normalised module face.
