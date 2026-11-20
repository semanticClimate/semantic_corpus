# Module `repositories` — literature repositories

**Status:** extension  
**Owner:** Larisa Beni  
**Spec:** [`MODULE_SPEC.md`](../MODULE_SPEC.md) · **Docs:** [`docs/modules/repositories/overview.md`](../../docs/modules/repositories/overview.md)

## Role

Repository adapters that harvest papers into the shared corpus contracts, including Europe PMC plus Global South and non-EN-centric sources (SciELO, Redalyc, CONICET, and related IRs).

## Docs

Module-specific notes: [`docs/`](docs/) (Latin America, South Asia, …).  
JOSS / strategy: [`docs/modules/repositories/`](../../docs/modules/repositories/).

## Facilities

See `module.yaml` (`europe_pmc`, `openalex`, `scielo`, `redalyc`, `conicet`, `la_irs`, `ids`).

## Public imports

```python
from semantic_corpus.repositories import MODULE_NAME, load_meta
from semantic_corpus.repositories.europe_pmc import EuropePMC  # example adapter
```

This package is both the normalised module face and the implementation home for repository adapters.
