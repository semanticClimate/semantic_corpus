# Branch: `larisaBeni`

**Remote tip:** `origin/larisaBeni` @ `efdd696` (*xml is finally available!*)  
**vs `origin/main`:** ahead **62**, behind **0**  
**Verdict:** **Highest-priority merge** for Latin American repository support.

---

## Why it matters

Extends the repository layer beyond Europe PMC/arXiv with working (or near-working) adapters and tests for regional open repositories, plus shared review/viewer infrastructure pulled through the `conicet` line.

**Contains** the entire `origin/conicet` tip — merging `larisaBeni` is enough; do not also merge `conicet`.

---

## Useful unmerged content

### Code (keep)

| Area | Paths (indicative) |
|------|--------------------|
| CONICET adapter | `semantic_corpus/repositories/conicet.py`, `tests/test_conicet.py` |
| UBA (Argentina) | `semantic_corpus/repositories/uba.py`, `tests/test_uba.py` |
| Kerwa (Costa Rica) | `semantic_corpus/repositories/kerwa.py`, `tests/test_kerwa.py` |
| UChile | `semantic_corpus/repositories/uchile.py`, `tests/test_uchile.py` |
| UNAL Colombia | `semantic_corpus/repositories/unal_colombia.py`, `tests/test_unal.py` |
| UNAM Mexico | `semantic_corpus/repositories/unam_mexico.py`, `tests/test_unam.py` |
| USP (São Paulo) | `semantic_corpus/repositories/usp.py` |
| ID helpers | `semantic_corpus/repositories/_ids.py` (extended) |
| Factory wiring | `semantic_corpus/core/repository_factory.py` |
| Review / viewer stack | `html_viewer.py`, `interactive_review.py`, `review_viewer_server.py`, `text_preview.py`, related tests |
| SciELO / Redalyc / OpenAlex | adapters + live smoke tests (also appear on tab_fig line — dedupe) |

### Docs (keep)

- `Conicet_repository.md`, `tutorials/Tutorial_conicet.md`
- `tutorials/generation_of_review_table.md`
- `docs/report_architecture.md`
- `problems_and_solutions.md` (issues/solutions narrative)
- `Larisa_dailyProgress.md` — optional; archive under internship notes rather than root

### Tests (keep)

`tests/test_uba.py`, `test_uchile.py`, `test_unal.py`, `test_unam.py`, `test_kerwa.py`, `test_conicet.py`, plus review-viewer / adapter tests.

---

## Leave out or strip before merge

- `build/lib/**` (packaging junk)
- `__pycache__/**` and `*.pyc`
- Large harvested XML/PDF trees and `tool_research/PMC*.xml` dumps unless intentionally versioning a small fixture set
- Duplicate agrochemicals paper corpora if they belong in a separate data store

---

## Suggested merge approach

```text
main ← merge larisaBeni (or PR)
  → .gitignore already excludes cache if present; verify
  → run adapter unit tests; live tests optional/manual
  → delete origin/conicet after green
```

Because **behind=0**, this is the cleanest large merge onto current `main`.
