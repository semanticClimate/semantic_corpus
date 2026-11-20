# Extension module specification

**Date:** 2026-11-16  
**Purpose:** Normalise how modular extensions of `semantic_corpus` are declared, documented, and discovered.  
**Authoritative human overview:** `docs/modules/README.md`

Every first-class extension is a **subpackage** of `semantic_corpus` with the **same layout and metadata**. Implementation code may still live in legacy paths (`core/`, `ingestion/`, `cluster_review/`, …) until moved; the module package is the **stable face** (metadata + public imports + docs pointer).

---

## Required layout

```
semantic_corpus/<module_name>/
  __init__.py      # MODULE_NAME, load metadata, re-export public API
  module.yaml      # declarative properties (required)
  README.md        # short human summary (required)
  docs/            # module-specific *.md (required; lists, notes, local design)
  facilities/      # optional: one file or subpackage per facility
```

Copy from `semantic_corpus/module_template/` when adding a new module.

**Docs split:** `semantic_corpus/<name>/docs/` holds material **specific to that module** (e.g. repository source lists). Top-level `docs/modules/<name>/` holds JOSS/series-facing overviews that may cross modules. Prefer adding new module-only notes under the package `docs/` folder.

---

## `module.yaml` fields

| Field | Required | Meaning |
|-------|----------|---------|
| `name` | yes | Package directory name (`corpus`, `repositories`, `phrases_kg`) |
| `title` | yes | Short display title |
| `summary` | yes | 1–2 sentences |
| `owner` | yes | Focus owner for the theme |
| `co_authors` | yes | Usually Renu + PMR on all papers |
| `status` | yes | `primary` \| `extension` \| `bridge` |
| `python_extra` | yes | Extra name or `null` |
| `depends_on` | yes | List of other module `name`s |
| `docs` | yes | Path to JOSS overview, usually `docs/modules/<name>/overview.md` (package also has `docs/`) |
| `legacy_paths` | no | Paths this module fronts |
| `facilities` | yes | List of capabilities (may be empty only while scaffolding) |

Each **facility** entry:

| Field | Required | Meaning |
|-------|----------|---------|
| `id` | yes | Stable slug |
| `title` | yes | Display name |
| `summary` | yes | One line |
| `entry` | no | Dotted import path for the main entry |

---

## Current modules

| name | status | Package |
|------|--------|---------|
| `corpus` | primary | `semantic_corpus.corpus` |
| `repositories` | extension | `semantic_corpus.repositories` |
| `phrases_kg` | extension | `semantic_corpus.phrases_kg` |

Bridges (encyclopedia, chatbot export) may gain the same layout later; until then they are described only under `docs/modules/README.md`.

---

## Discovery

```python
from semantic_corpus.module_meta import list_modules, load_module

for meta in list_modules():
    print(meta["name"], meta["title"], meta["owner"])
```

---

## Rules

1. Do **not** invent a parallel BagIt/ID vocabulary inside an extension.  
2. Extensions **depend on** `corpus` contracts unless they *are* `corpus`.  
3. Docs in `docs/modules/<name>/overview.md` must match `module.yaml` names.  
4. New facilities are declared in `module.yaml` before being advertised in JOSS text.  
5. Follow [coding_style.md](../docs/coding_style.md) (including **no mocks**).
