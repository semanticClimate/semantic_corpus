# Tutorial: query → papers↔terms knowledge graph

**Goal:** Europe PMC search → interactive **paper ↔ term** graph.  
**Time:** a few minutes for a small limit (network + phrase extraction).  
**Examples index:** [pipeline_examples.md](../pipeline_examples.md).

---

## 0. Setup (once)

```bash
cd /path/to/semantic_corpus
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -e '.[cluster_review]'
```

Console script: **`pipeline`** (or `./venv/bin/pipeline`).

---

## 1. Example — AMOC, 30 papers (plain KG)

```bash
./venv/bin/pipeline \
  --workdir corpora/amoc_30 \
  --query "AMOC" \
  --limit 30 \
  --target clusters \
  --kg
```

| Flag | Value | Meaning |
|------|-------|---------|
| `--query` | `AMOC` | Live collect via EPMC |
| `--limit` | `30` | Max hits |
| `--target` | `clusters` | Through map |
| `--kg` | on | **KG₁** — incidence graph, no Wikipedia yet |
| `--open` | on | Open `kg/knowledge_graph.html` |

**Colors:** orange = papers (hover for title), blue = terms.

---

## 2. What you get

```text
corpora/amoc_30/
  bagit.txt
  data/…
  phrases/
  clusters/
  kg/
    knowledge_graph.html   ← interactive graph (KG₁)
    graph.json
    islands.json
```

Re-open later:

```bash
open corpora/amoc_30/kg/knowledge_graph.html   # macOS
# or rebuild helper:
./venv/bin/pipeline kg --workdir corpora/amoc_30
```

---

## 3. Continue: clean → encyclopedia + annotated KG

```bash
./venv/bin/pipeline --workdir corpora/amoc_30 --target clean
./venv/bin/pipeline --workdir corpora/amoc_30 --target encyclopedia --kg
```

**KG₂** adds Wikipedia payloads (and can include Wikidata via `--kg-links`).

**Fresh remake:**

```bash
./venv/bin/pipeline run --always \
  --workdir corpora/amoc_30 \
  --query "AMOC" --limit 30 \
  --target clusters --kg
```

**Headless / CI:**

```bash
./venv/bin/pipeline --workdir corpora/amoc_30 \
  --query "AMOC" --limit 30 --target clusters --kg --no-open
```

---

## 4. Troubleshoot

| Symptom | Fix |
|---------|-----|
| `doit` missing | `pip install -e '.[cluster_review]'` |
| Skips the query | Use `run --always`, or a new `--workdir` |
| Too many blue nodes | Raise `--kg-min-paper-count` or lower `--kg-max-terms` |
| No hover titles | Hard-reload the HTML after rebuild |
| Browser opens unwanted | Pass `--no-open` |
| `FileNotFoundError: …\.doit.db.dat` (Windows) | Store doit DB outside the bag (current pipeline); delete stale `corpora/<name>/.doit.db*` leftovers |

More: [pipeline.md](../pipeline.md) · [pipeline_examples.md](../pipeline_examples.md) · [pipeline_kg_mappers.md](../pipeline_kg_mappers.md)
