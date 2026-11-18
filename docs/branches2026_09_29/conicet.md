# Branch: `conicet`

**Remote tip:** `origin/conicet` @ `4c44989` (*quick tutorial*)  
**vs `origin/main`:** ahead **43**, behind **0**  
**Verdict:** Useful historically; **do not merge separately** — fully contained in `larisaBeni`.

---

## Useful content (already in `larisaBeni`)

- `semantic_corpus/repositories/conicet.py` + factory registration
- `_ids.py` CONICET identifier support
- `tests/test_conicet.py`
- Review table tutorials / viewer work shared with vrinda line
- `tutorials/Tutorial_conicet.md`, `Conicet_repository.md`
- Agrochemicals-related query/review experiments (content; optional archive)

---

## Action

1. Merge **`larisaBeni`** into `main` (includes this tip).  
2. Delete `origin/conicet` after verifying tip ancestry:  
   `git merge-base --is-ancestor origin/conicet origin/larisaBeni` → true as of 2026-09-29.
