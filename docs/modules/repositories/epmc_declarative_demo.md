# Team demo — declarative Europe PMC query (limit 2)

**Module:** [`repositories`](overview.md)  
**Controls:** [declarative_controls.md](declarative_controls.md)  
**Config:** [`config/epmc_limit2_demo.yaml`](../../../config/epmc_limit2_demo.yaml)  
**Prompt:** [discussions/prompt_2026-11-19_epmc_declarative_demo_docs.md](../../../discussions/prompt_2026-11-19_epmc_declarative_demo_docs.md)

---

## Question

> Please give an example of a query to EPMC using the declarative approach that I can demonstrate to the team on the command line. Limit to 2 papers as EPMC is slow.

---

## Answer (demo recipe)

### 1. Declarative pilot (edit YAML, not Python)

[`config/epmc_limit2_demo.yaml`](../../../config/epmc_limit2_demo.yaml):

```yaml
query_name: epmc_limit2_demo
query_string: '("marine heatwave" OR "ocean heatwave") AND (HAS_FT:Y)'
repository: europe_pmc
limit: 2
start_date: "2020-01-01"
end_date: "2026-12-31"
formats:
  - xml
  - pdf
corpus_name: epmc_limit2_demo
output_subdir: epmc_limit2_demo
timing: summary
```

Show the team: change `query_string`, `limit`, or dates **only in this file**.

### 2. Command line

```bash
cd /path/to/semantic_corpus

./venv/bin/python scripts/build_example_corpus.py \
  --config config/epmc_limit2_demo.yaml
```

### 3. What they should see

| Step | Outcome |
|------|---------|
| Search | Boolean EPMC query with date window |
| Download | Up to **2 new** papers (XML + PDF) |
| Layout | Packets under `temp/queries/epmc_limit2_demo/data/packets/` |
| Review | `temp/queries/epmc_limit2_demo/review/review_table.md` |
| Ingest | BagIt corpus `corpora/epmc_limit2_demo/` (`data/documents/{pdf,xml,html}/`, metadata) |

### 4. Rerun (add 2 more)

Same command again (do **not** use `--reuse-existing`):

```bash
./venv/bin/python scripts/build_example_corpus.py \
  --config config/epmc_limit2_demo.yaml
```

- Skips papers already on disk  
- Downloads **2 new** hits  
- Merges into growing `search_results.json` and corpus  

### 5. If Europe PMC returns 503

EPMC may be temporarily unavailable. Either wait and retry the live command, or finish from the last successful query dir **without** new papers:

```bash
./venv/bin/python scripts/build_example_corpus.py \
  --config config/epmc_limit2_demo.yaml \
  --reuse-existing
```

---

## Talking points for JOSS / strategy

1. **Declarative** — repository + query + limit + dates in YAML.  
2. **Personal corpus** — bounded `limit`, interrupt/resume friendly.  
3. **Hand-off to `corpus`** — BagIt + review table, not a loose PDF folder.  
4. **Sibling story** — this is the `repositories` → `corpus` dotted edge ([../corpus/siblings.md](../corpus/siblings.md)).
