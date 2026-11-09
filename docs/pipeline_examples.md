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

**Plan:** `search → collect (paper:*) → corpus → phrases → clusters` (+ KG₁).

During **collect**, titles scroll in a live terminal window as each EPMC paper
downloads (`+` new, `=` already on disk). Files are flat under `--workdir`
(`PMC….json|.xml|.pdf|.pdf.xml`).

**Artifacts**

- Corpus: `corpora/amoc_30/` (flat paper files + `search_results.json`)
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
./venv/bin/pipeline --workdir corpora/amoc_30 \
  --phrase-limit 40 --document-limit 30 --min-paper-count 2 \
  --target encyclopedia --kg
```

**Caps**

| Flag | Role |
|------|------|
| `--phrase-limit N` | Max phrases resolved / display-KG term nodes |
| `--document-limit N` | Max papers contributing to encyclopedia + display KG |
| `--min-paper-count N` | Drop rare terms (`n_papers`) |
| `--cluster-resolution R` | Louvain: **`< 1` fewer/larger clusters** (aggregate); `> 1` more fragments |

**Interactive viewer** (`--view`: local page + API; Louvain rebuild ~ms):

```bash
./venv/bin/pipeline kg --workdir corpora/amoc_30 --view
# opens the KG; drag Louvain resolution to re-aggregate live
```

---

## More examples

*(Add further numbered scenarios here — e.g. static `--source`, full spine to encyclopedia, annotated KG with Wikidata.)*
