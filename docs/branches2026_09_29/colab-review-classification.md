# Branch: `colab-review-classification`

**Remote tip:** `origin/colab-review-classification` @ `6edc2a2`  
**vs `origin/main`:** ahead **1**, behind **30**  
**Verdict:** **Yes — merge/rebase** as a focused feature PR.

---

## Why it matters

Single coherent commit adding paper **classification** for review tables, Colab notebook updates, and tests — high signal, low noise compared with internship corpus branches.

---

## Useful unmerged content

| Path | Role |
|------|------|
| `semantic_corpus/classification/` | `annotate.py`, `encyclopedia_labels.py`, `unsupervised.py` |
| `scripts/classify_review_table.py` | CLI entry |
| `notebooks/corpus_query_review_colab.ipynb` | Colab review + PDF links + classification |
| `tests/test_classification.py` | Unit tests |
| Updates to `corpus_review/*`, `docs/colab_corpus_review_notebook.md`, `docs/build_review_table.md` | Integration with review workflow |
| `pyproject.toml` | Likely new deps — verify before merge |

---

## Caveats

- Rebase onto post-`larisaBeni`/`tab_fig` `main` — may conflict in `review_schema.py` / `constants.py` / `workflow.py`.  
- Confirm classification deps are acceptable for default installs (optional extras if heavy).

---

## Suggested merge approach

```text
git checkout -b feat/classification origin/colab-review-classification
git rebase origin/main
# fix conflicts, run pytest tests/test_classification.py
# PR → main
```
