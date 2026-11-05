# Tutorial: query → papers↔terms knowledge graph

**Goal:** run a Europe PMC search and open an interactive **paper ↔ term** graph in one command.  
**Time:** a few minutes for a small limit (network + phrase extraction).

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

## 1. One command

```bash
./venv/bin/pipeline \
  --workdir corpora/amoc_demo \
  --query "amoc AND insolation" \
  --target kg
```

Defaults already do the rest:

| Default | Value | Meaning |
|---------|-------|---------|
| `--limit` | `20` | Max Europe PMC hits |
| `--kg-links` | `clusters` | Bipartite **paper ↔ term** edges |
| `--kg-min-paper-count` | `2` | Drop rare terms |
| `--kg-max-terms` | `40` | Cap blue term nodes |
| `--open` | on | Open `kg/knowledge_graph.html` when done |

**Colors:** orange = papers (hover for title), blue = terms.

Override any of them explicitly when needed (`--limit 50`, `--kg-links clusters,wikipedia`, `--no-open`, …).

---

## 2. What you get

```text
corpora/amoc_demo/
  bagit.txt
  data/…
  phrases/
  clusters/
  kg/
    knowledge_graph.html   ← interactive graph
    graph.json
    islands.json
    kg_summary.json
```

Re-open later without rebuilding:

```bash
open corpora/amoc_demo/kg/knowledge_graph.html   # macOS
# or:
./venv/bin/pipeline kg --workdir corpora/amoc_demo
```

---

## 3. Useful variants

**Fresh remake** (ignore skip-if-done stamps):

```bash
./venv/bin/pipeline run --always \
  --workdir corpora/amoc_demo \
  --query "amoc AND insolation" \
  --target kg
```

**Merge synonym terms** (needs a prior encyclopedia build with Wikipedia resolves):

```bash
./venv/bin/pipeline encyclopedia --workdir corpora/amoc_demo \
  --min-paper-count 2 --max-entries 50 --force

./venv/bin/pipeline kg --workdir corpora/amoc_demo \
  --kg-links clusters,wikipedia
```

**Existing corpus only** (no new search):

```bash
./venv/bin/pipeline --workdir corpora/amoc_demo --target kg
```

**Headless / CI** (don’t open a browser):

```bash
./venv/bin/pipeline --workdir corpora/amoc_demo --query "…" --target kg --no-open
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
| `FileNotFoundError: …\.doit.db.dat` (Windows) | Upgrade past the fix that stores the doit DB outside the bag; delete any stale `corpora/<name>/.doit.db*` and `data/.doit.db*` leftovers, then re-run |

More detail: [pipeline.md](../pipeline.md) · [pipeline_next_encyclopedia_kg.md](../pipeline_next_encyclopedia_kg.md)
