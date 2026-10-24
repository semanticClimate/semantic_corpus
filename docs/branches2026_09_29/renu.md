# Branch: `renu`

**Remote tip:** `origin/renu` @ `faf100d` (*Add tutorial for building semantic corpus from custom queries*)  
**vs `origin/main`:** ahead **15**, behind **30**  
**Verdict:** **Cherry-pick** onto `main` after `tab_fig` — do not merge as a second full stack.

---

## Relation to `tab_fig`

Same feature line. Diff vs `tab_fig` is small:

| On `renu` only | On `tab_fig` only |
|----------------|-------------------|
| `docs/tutorials/build_semantic_corpus_on_query.md` | `docs/outreach/citizen_science_climate_knowledge_prospectus.md` |
| `create_query.py` | (demo README updates tied to outreach) |

Almost everything else useful on `renu` is already on `tab_fig` (ocean heatwaves docs, PRISMA, adapters, fixtures).

---

## Useful unmerged content (unique)

1. **`docs/tutorials/build_semantic_corpus_on_query.md`** — end-user tutorial for custom queries (high value for consolidation).  
2. **`create_query.py`** — helper script; include if still the supported entry point, else fold into `scripts/`.

---

## Action

```text
After tab_fig → main:
  git cherry-pick <commit(s) for tutorial + create_query.py>
  or checkout those paths from origin/renu
Delete origin/renu when done.
```
