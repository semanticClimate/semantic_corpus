# Pipeline examples

**Parent:** [pipeline.md](pipeline.md) · design [pipeline_kg_mappers.md](pipeline_kg_mappers.md)

Spine: `collect → corpus → phrases → clusters → clean → encyclopedia`  
Display graphs: `--kg` on `clusters` (**KG₁**, plain) or `encyclopedia` (**KG₂**, Wikipedia-annotated).

---

## 1. AMOC — 30 papers → clusters + plain KG

Europe PMC search `AMOC`, cap **30** hits, build the bipartite graph and open **KG₁** (no encyclopedia yet).

```bash
./venv/bin/pipeline \
  --workdir corpora/amoc_30 \
  --query "AMOC" \
  --limit 30 \
  --target clusters \
  --kg
```

| Flag | Value | Role |
|------|-------|------|
| `--workdir` | `corpora/amoc_30` | BAGIT corpus + stamps |
| `--query` | `AMOC` | Live collect (EPMC) |
| `--limit` / `-n` | `30` | Max papers |
| `--target` | `clusters` | Plan through map |
| `--kg` | on (default) | Write/open plain display KG |

**Plan:** `collect → corpus → phrases → clusters` (+ KG₁).

**Artifacts**

- Corpus: `corpora/amoc_30/`
- Harvest: `temp/queries/amoc_30/`
- Graph HTML: `corpora/amoc_30/kg/knowledge_graph.html`

**Remake** (ignore skip-if-done):

```bash
./venv/bin/pipeline run --always \
  --workdir corpora/amoc_30 \
  --query "AMOC" --limit 30 \
  --target clusters --kg
```

**Next on the same workdir** (curate, then annotate + KG₂):

```bash
./venv/bin/pipeline --workdir corpora/amoc_30 --target clean
./venv/bin/pipeline --workdir corpora/amoc_30 --target encyclopedia --kg
```

---

## More examples

*(Add further numbered scenarios here — e.g. static `--source`, full spine to encyclopedia, annotated KG with Wikidata.)*
