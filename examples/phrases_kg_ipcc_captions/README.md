# Example — IPCC figure captions → bipartite KG (`phrases_kg` sample)

**Owners (module):** Neel Kumar + Anusha · **Handoff:** [`indexed_text_handoff.md`](../../docs/modules/phrases_kg/indexed_text_handoff.md) · **Schema:** [`indexed_text.schema.json`](../../semantic_corpus/corpus/schemas/indexed_text.schema.json) · **Types:** [`corpus.types`](../../semantic_corpus/corpus/types/)
Sample inputs mirror the intended `phrases_kg` path: **captions as `indexed_text`** (`kind: figcaption`) + **term list** (JSON array of strings; Goal 1 skipped).

## Data

| File | Role |
|------|------|
| [`data/ipcc_ar6_wgii_ch02.indexed.json`](data/ipcc_ar6_wgii_ch02.indexed.json) | Chapter 2 captions as `indexed_text` |
| [`data/ipcc_ar6_wgii_ch04.indexed.json`](data/ipcc_ar6_wgii_ch04.indexed.json) | Chapter 4 captions as `indexed_text` (incl. Figs 4.27 / 4.28 / 4.31 style) |
| [`data/terms.json`](data/terms.json) | Array of term strings appearing in those captions |

Ch2 captions are **thematic paraphrases** for the demo; Ch4 tracks public IPCC figure pages more closely. Replace with verbatim captions for research packs.

## Run

```bash
# networkx required; matplotlib optional (PNG)
pip install networkx matplotlib

python examples/phrases_kg_ipcc_captions/build_bipartite_kg.py
# → prints term↔caption edges
# → writes examples/phrases_kg_ipcc_captions/out/
#      ipcc_captions_bipartite.graphml
#      ipcc_captions_bipartite.edges.json
#      ipcc_captions_bipartite.png   (if matplotlib present)
```

## Graph model (this sample)

- **Left nodes:** terms from `terms.json`  
- **Right nodes:** `text_block` ids with `kind: figcaption`  
- **Edge:** term occurs in caption text (case-insensitive; longer phrases matched first)

This is a minimal stand-in for `phrases_kg` Goal 2 (`graph_mode: bipartite`, `document_unit: caption`). Production code should live under `semantic_corpus/phrases_kg/` and honour [controls.md](../../docs/modules/phrases_kg/controls.md).
