# Corpus BagIt structure

**Status:** design contract for `--workdir` as a portable corpus root.  
**Related:** [pipeline.md](pipeline.md) · [pipeline_kg_mappers.md](pipeline_kg_mappers.md)  
**Spec:** [RFC 8493 (BagIt)](https://www.rfc-editor.org/rfc/rfc8493.html)

## Goals

- `--workdir` is the **root of one corpus**: copy, lift, or delete as a unit.
- **Map/reduce:** raw and transformed document bytes are mapped per packet; gathered products and run metadata sit in clear siblings.
- **Human-friendly** layout with **explicit semantics** (especially transform history in filenames).
- Stay **BagIt-compatible** so payload can be checksummed and validated.

## BagIt reserved names

Only these names are special at the bag root:

| Name | Role |
|------|------|
| `data/` | **Required** payload directory |
| `bagit.txt` | **Required** BagIt declaration |
| `manifest-<alg>.txt` | **Required** (≥1): checksums of every file under `data/` |
| `bag-info.txt` | Optional bag metadata |
| `tagmanifest-<alg>.txt` | Optional checksums of tag files |
| `fetch.txt` | Optional remote payload list (“holey” bag) |

Anything else at the bag root is a **tag file** or **tag directory** (must not collide with the names above).

**Not reserved:** `packets/`, `indexes/`, `pipeline/`, `review/`, `corpus.json`, `search_results.json`, etc. We still use `indexes/` under `data/` for reduce products.

Payload paths in manifests are relative to the bag root and must stay under `data/` (e.g. `data/packets/PMC1.pdf`).

## Layout

```text
corpora/amoc_200/                    # --workdir = bag root (portable unit)
  bagit.txt
  bag-info.txt                       # optional; query / limit / provenance
  manifest-sha256.txt
  tagmanifest-sha256.txt             # optional
  corpus.json                        # tag: identity, term-set pins
  search_results.json                # tag: intake hit list
  review/                            # tag: human review tables
  pipeline/                          # tag: step stamps + doit.db (tooling)
  data/                              # REQUIRED payload
    packets/                         # MAP: raw + transforms
      PMC12345.json                  # metadata / abstract
      PMC12345.pdf
      PMC12345.xml                   # publisher / EPMC XML
      PMC12345.pdf.xml               # Docling: PDF → XML
      PMC12345.pdf.html              # Docling: PDF → HTML (optional)
    indexes/                         # REDUCE: gathered products (checksummed)
      packets.json                   # packet inventory / addresses
      phrases/
      clusters/
      encyclopedia/                  # when encyclopedia is corpus-bound
```

Shared annotation vocabulary lives **outside** any one workdir:

```text
terms/                               # high-level, reusable across corpora
  amoc_core/
    glossary.json
```

A corpus **pins** term sets by reference in `corpus.json` (path or id). Full copyability of an experiment may need a freeze/export step that snapshots referenced terms.

## Map vs reduce vs tags

| Kind | Where | Examples |
|------|--------|----------|
| **Map** (per packet) | `data/packets/` | `{id}.json`, `{id}.pdf`, `{id}.xml`, `{id}.pdf.xml` |
| **Reduce** (over packets) | `data/indexes/` | phrases, clusters, packet inventory |
| **Tags** (beside `data/`) | bag root | `corpus.json`, `search_results.json`, `review/`, `pipeline/` |
| **Shared terms** | outside workdir | `terms/…` |

**Rule of thumb**

- Under `data/`: bytes you archive and verify.
- Beside `data/`: regenerable tooling or process metadata (`pipeline/`), plus light intake/review tags.
- Outside the workdir: shared `terms/`.

## Packet files and suffix history

A **packet** is one logical document unit (today: one paper). Multiple files for the same packet share the id stem; **suffixes encode type and transform history** (left → right):

| Pattern | Meaning |
|---------|---------|
| `{id}.json` | Metadata / abstract |
| `{id}.xml` | Publisher / EPMC fullTextXML |
| `{id}.pdf` | Native PDF |
| `{id}.pdf.xml` | Derived XML from PDF (e.g. Docling) |
| `{id}.pdf.html` | Derived HTML from PDF |

**Text cascade** for phrases/packets: prefer `{id}.xml`, else `{id}.pdf.xml`, else abstract in `{id}.json`.

### Deeper nesting?

**Default: no.** Flat `data/packets/{id}.{suffix…}` is the preferred human surface.

Use a per-id directory only when the packet is a **bundle** (supplements, many figures, chapter slices):

```text
data/packets/PMC12345/
  PMC12345.pdf
  PMC12345.pdf.xml
  …
```

Avoid per-format trees like `data/packets/pdf/` — that fights “open this packet” browsing and map/reduce clarity.

## Why `data/packets/` (not flat bag root)

Python `bagit.make_bag()` expects a real bag: payload under `data/`, manifests at the root. Putting science files at the bag root collides with tag space and with library behaviour that can move top-level files into `data/` on create. Keeping map/reduce under `data/` and tooling under tag dirs (`pipeline/`) matches the spec and avoids that trap.

## Pluses and minuses

**Pluses**

- Portable unit: one directory is the experiment.
- Explicit map/reduce and BagIt integrity for payload.
- Human browse: `ls data/packets/PMC123*` shows everything for that paper.
- Transform history in filenames without a sidecar DB.
- Terms reusable across corpora.

**Minuses / risks**

- BagIt adds reserved names and manifest maintenance (`manifest-*.txt` must list every payload file).
- Shared `terms/` breaks “one folder = whole experiment” unless pins/export are disciplined.
- Suffix grammar must stay strict; ambiguous names erode provenance.
- Very large flat `packets/` directories can stress some filesystems (shard later only as an operational escape hatch).
- Legacy corpora using `data/documents/{fmt}/` need resolvers or migration.

## Collect vs lazy PDFs

| Step | Writes | Skips |
|------|--------|-------|
| `search` | `search_results.json`, light `bagit.txt` | — |
| `collect` | `{id}.json`, `{id}.xml` under `data/packets/` | Papers with JSON + XML (or recorded XML miss) |
| `pdfs` | `{id}.pdf` (optional `{id}.pdf.xml` via Docling) | Existing valid PDFs; use `--paper-id` for one paper |

PDFs are typically **gitignored** (`corpora/**/*.pdf`). Indexing does not require them.

Tutorials: [pipeline_epmc_resume.md](tutorials/pipeline_epmc_resume.md) · [lazy_pdfs.md](tutorials/lazy_pdfs.md).

## Implementation notes

- Doit / pipeline stamps and `doit.db` belong under **`pipeline/`** (tag directory), not under `data/`.
- New harvests write packet bytes to **`data/packets/`** with history suffixes; reduce artifacts to **`data/indexes/`**.
- Legacy BAGIT layouts (`data/documents/…`, nested `data/data/…`) and flat workdir roots remain readable via resolvers until migrated.
