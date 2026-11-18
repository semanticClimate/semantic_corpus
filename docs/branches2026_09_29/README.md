# Branch consolidation audit — 2026-09-29

**Date:** 2026-09-29 (system date of generation)  
**Base for comparison:** `origin/main` @ `aae286e` (*Delete corpora/akalya_project/zip*)  
**Goal:** shrink active branches and fold useful work into `main`

---

## Snapshot

| Remote branch | Ahead of `main` | Behind `main` | Useful for `main`? | Notes |
|---------------|-----------------|---------------|--------------------|-------|
| **larisaBeni** | 62 | 0 | **Yes — primary** | Latin American adapters + review stack; **contains `conicet`** |
| **conicet** | 43 | 0 | Yes (via larisa) | Fully contained in `larisaBeni`; do not merge separately |
| **tab_fig** | 14 | 30 | **Yes — primary** | Ocean heatwaves demo, review viewer, PRISMA, citizen prospectus |
| **renu** | 15 | 30 | **Yes — cherry-pick** | Same line as `tab_fig` + query tutorial; missing citizen prospectus |
| **vrinda** | 23 | 30 | **Yes — content** | Climate anxiety curated corpus + encyclopedia artefacts + tutorials |
| **colab-review-classification** | 1 | 30 | **Yes — code** | Classification package + Colab notebook + tests (small, clean) |
| **subhangi** | 7 | 0 | Partial | Internship AQI review HTML; also committed `__pycache__` |
| **Ilakkya-S** | 27 | 30 | Archive only | Personal AQI docs + large zip/video/XML dumps |
| **akalya** | 7 | 30 | Archive only | Plant–climate internship corpus under `docs/` |
| **shreya** | 38 | 30 | Archive / sample | Global warming query + review editor HTML; bulky XML |
| **gulamajdhani** | 2 | 37 | No | Added then deleted progress report — empty delta |
| **ila** | 0 | 30 | No | No unique commits vs `main` |

**Local-only extras (not on remote tip):**

- `subhangi` local tip `f39600c` — PRISMA diagram prototype (overlaps code also present on `tab_fig`/`renu`)
- Current checkout: `tab_fig` (matches `origin/tab_fig`)
- Local `main` is **30 commits behind** `origin/main` (mostly akalya corpus deletions)

---

## Recommended merge order into `main`

1. **`larisaBeni`** — largest code win; already based on current `origin/main` (`behind=0`). Bring Latin American repository adapters + shared review/viewer work. Strip `build/`, `__pycache__`, and bulk paper dumps before or during merge.
2. **`colab-review-classification`** — small, focused classification feature; rebase onto updated `main` after step 1.
3. **`tab_fig`** (or merge `tab_fig` then cherry-pick renu’s tutorial) — ocean heatwaves fixtures/docs, PRISMA, OpenAlex/SciELO/Redalyc (if not already from larisa line), citizen prospectus. Expect conflicts; branch is **30 behind**.
4. **`renu`** — cherry-pick only:
   - `docs/tutorials/build_semantic_corpus_on_query.md`
   - `create_query.py` (if still wanted)
5. **`vrinda`** — selectively: tutorials + analysis/provenance markdown + encyclopedia HTML/keyphrases; **do not** merge entire nested BAGIT/XML trees unless you accept a large binary/data commit.
6. **Internship corpus branches** — do **not** merge wholesale. Optionally archive a thin sample (README + curated review CSV/JSON) under `docs/internship_archive/` or release as a separate data repo.

Then delete or archive remote branches that are superseded.

---

## Suggested end state (fewer active branches)

| Keep | Role |
|------|------|
| `main` | Sole integration branch |
| short-lived feature branches | e.g. `feat/…` opened from `main`, PRs, then delete |

| Delete after merge / archive | Reason |
|------------------------------|--------|
| `conicet` | Contained in `larisaBeni` |
| `ila` | Empty |
| `gulamajdhani` | Empty |
| `Ilakkya-S`, `akalya`, `shreya`, `subhangi` | Internship dumps; archive samples if needed |
| `larisaBeni`, `tab_fig`, `renu`, `vrinda`, `colab-review-classification` | After their useful content is on `main` |

---

## What `origin/main` currently lacks

Compared with the feature branches, `main` still has a thin platform:

- Repositories: **arxiv + europe_pmc only** (no SciELO/Redalyc/OpenAlex/CONICET/UBA/…)
- No review HTML viewer / interactive review server
- No PRISMA flow/diagram modules
- No classification package
- No ocean heatwaves / climate anxiety demo docs under `docs/demo/`
- No Latin American adapter tests

So consolidation is not “cleanup of stale tips” only — **most recent product work lives off `main`.**

---

## Per-branch notes

| File | Branch |
|------|--------|
| [larisaBeni.md](larisaBeni.md) | Primary LATAM adapters (+ contains conicet) |
| [conicet.md](conicet.md) | CONICET adapter line (superseded) |
| [tab_fig.md](tab_fig.md) | Ocean heatwaves + citizen outreach |
| [renu.md](renu.md) | Tutorial-focused sibling of tab_fig |
| [vrinda.md](vrinda.md) | Climate anxiety encyclopedia corpus |
| [colab-review-classification.md](colab-review-classification.md) | Classification + Colab |
| [internship_and_misc.md](internship_and_misc.md) | Ilakkya-S, akalya, shreya, subhangi, gulamajdhani, ila |

---

## Caveats for merging

1. **Huge diffs** on `larisaBeni` / `tab_fig` / `vrinda` include XML, PDF, zip, HTML corpora, and sometimes `build/` or `__pycache__`. Prefer merging **code + docs + small fixtures**, not full harvest trees.
2. **`tab_fig` / `renu` / `vrinda` / `colab-review-classification`** share older history and are **30 commits behind** `main` — rebase or merge carefully.
3. Overlap: review-viewer and SciELO/Redalyc/OpenAlex appear on both the **conicet/larisa** line and the **tab_fig/vrinda** line; land one clean version on `main` and drop duplicates.
4. Do not treat GitHub “Add files via upload” internship folders as production source of truth.
