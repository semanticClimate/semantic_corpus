# For Neel & Anusha — `indexed_text` input to `phrases_kg`

**Date:** 2026-11-26  
**Audience:** phrases_kg (bipartite KG / captions) · also useful for chatbot  
**Owner of the type:** `corpus/` (do not fork a parallel schema in phrases_kg)

---

## What you consume

Your module does **not** own ingest. You receive **`indexed_text`**: one document after sectioning, with:

- stable **`paper_id`**
- **`metadata`** (title, citation_label, …)
- **`blocks[]`** — each a `text_block` with **`id`**, **`kind`**, **`text`**, **`order`**

For IPCC figure work, filter `blocks` where **`kind == "figcaption"`**. Pair with a **term list** (JSON array of strings for now). Build the bipartite graph **term ↔ block id**; do not invent a second chunk vocabulary.

`phrases_kg` and **chatbot** both read `indexed_text` **independently** (no dependency on each other).

```text
repositories / legacy  →  indexed_text  →  phrases_kg  →  knowledge_graph
                              ↓
                           chatbot
```

---

## Schema & code (use these, don’t copy strings)

| What | Where |
|------|--------|
| **JSON Schema** | [`semantic_corpus/corpus/schemas/indexed_text.schema.json`](../../../semantic_corpus/corpus/schemas/indexed_text.schema.json) |
| **Prose spec** | [`semantic_corpus/corpus/docs/indexed_text.md`](../../../semantic_corpus/corpus/docs/indexed_text.md) |
| **Python enums / loaders** | `from semantic_corpus.corpus.types import BlockKind, load_indexed_texts, blocks_of_kinds, …` |
| **Pilot controls** | [`controls.md`](controls.md) (`document_unit: caption`, `graph_mode: bipartite`, `input.terms` / `terms_path`) |

Required top-level fields: `type` (`"indexed_text"`), `paper_id`, `id_scheme`, `blocks` (≥1), `metadata` (object, may be `{}`).

---

## Example files to open

| File | Notes |
|------|--------|
| [`examples/phrases_kg_ipcc_captions/data/ipcc_ar6_wgii_ch02.indexed.json`](../../../examples/phrases_kg_ipcc_captions/data/ipcc_ar6_wgii_ch02.indexed.json) | Ch2 captions |
| [`examples/phrases_kg_ipcc_captions/data/ipcc_ar6_wgii_ch04.indexed.json`](../../../examples/phrases_kg_ipcc_captions/data/ipcc_ar6_wgii_ch04.indexed.json) | Ch4 captions (4.27 / 4.28 / 4.31 style) |
| [`examples/phrases_kg_ipcc_captions/data/terms.json`](../../../examples/phrases_kg_ipcc_captions/data/terms.json) | Term list = JSON **array of strings** |
| [`examples/phrases_kg_ipcc_captions/build_bipartite_kg.py`](../../../examples/phrases_kg_ipcc_captions/build_bipartite_kg.py) | Minimal sample: load → match → NetworkX bipartite |

Run:

```bash
python examples/phrases_kg_ipcc_captions/build_bipartite_kg.py
```

---

## Minimal block shape (what you iterate)

```json
{
  "id": "ipcc_ar6_wgii_ch04#figcaption-001",
  "kind": "figcaption",
  "text": "Figure 4.27 | … water-related adaptation …",
  "order": 1,
  "parent_id": "ch04-figures"
}
```

Prefer keeping **`blocks[].id`** on every KG edge / export so citations stay stable.

---

## Do / don’t

| Do | Don’t |
|----|--------|
| Import types from `semantic_corpus.corpus.types` | Redefine `kind` / field names in phrases_kg |
| Filter by `BlockKind.FIGCAPTION` (or `--kinds`) | Treat whole chapter as one opaque string if blocks exist |
| Accept missing `html` / bbox | Require BagIt layout |
| Emit `knowledge_graph` as *your* output | Put KG or chat state inside `indexed_text` |

---

## One sentence

**`indexed_text` is the shared, schema-validated hand-off: sectioned text with stable block ids + metadata; phrases_kg turns selected blocks (e.g. figcaptions) plus a term list into a bipartite knowledge graph.**
