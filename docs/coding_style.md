# Coding style — semanticClimate repositories

**Status:** draft for agreement (2026-11-16, system date)  
**Applies to:** `semantic_corpus` and sibling AMI / semanticClimate Python repos unless a repo overrides  
**Inherits:** [pygetpapers styleguide](../../pygetpapers/docs/styleguide.md) and [amilib style_guide_compliance](../../amilib/docs/style_guide_compliance.md) (absolute imports, empty `__init__.py`, no `sys.path`/PYTHONPATH, Path construction, climate examples, dates, **no mocks**, development protocol)

After we agree this text, we will walk the codebase (optionally with the team watching) and note deviations for fix or explicit exception.

---

## 0. No mocks

**Do not use mocks, patches, fakes, or `monkeypatch.setattr` on production collaborators in tests.** Prefer real implementations, real files under `tests/resources` / temp dirs, and — for remote services — either a **live** call gated by `SC_LIVE_API=1` or a **recorded fixture on disk** (JSON/XML/PDF bytes), not a pretend `requests.get`.

- ❌ `unittest.mock`, `pytest-mock`, `@patch`, MagicMock, stubbing `EuropePMCRepository.search`, muting `epmc_preflight` in conftest  
- ✅ Call the real code path; assert on returned structures and files  
- ✅ Live EPMC/OpenAlex checks: mark `live_api` / `network`, require `SC_LIVE_API=1`, fail or skip clearly on outage — do not fake success  
- ✅ Offline unit tests: use small **real** sample files; if the network is required, skip with an explicit message rather than mock  

**Rationale (amilib):** mocks hide integration bugs and teach a false green. ECRs should see the same failures they will see on a laptop (including “EPMC is down”).

**Known debt:** some existing tests/conftest still mock or mute EPMC; treat that as violation to remove, not as precedent.

---

## 1. Prefer existing open-source libraries

- Before writing a new parser, HTTP client helper, HTML cleaner, CSV/JSON util, or CLI framework, **check whether a maintained library already does it** (stdlib first, then well-known OSS).
- Prefer **dependencies already in the project** over adding a new one for a one-liner.
- If you reimplement, document **why** (licence, size, offline, semantic HTML fidelity, etc.).
- Do **not** vendor large trees of third-party code into the repo without agreement.

---

## 2. Externalise what readers will inspect or edit

Anything likely to be read or changed by people who are **not** maintaining the Python package should live in **declarative files**, not buried in `.py` string literals.

| Prefer external | Examples |
|-----------------|----------|
| **JavaScript** | Review-table behaviour, small UI scripts → `.js` under `assets/` or similar |
| **CSS** | Layout and theme → `.css` (already partly done for review tables) |
| **JSON / YAML** | Query configs, schemas, fixtures, manifests, label lists |
| **XML / HTML templates** | Sample documents, static markup shells (not giant `"""..."""` in Python) |
| **Markdown** | Tutorials, human procedures, review notes |

**Also externalise near-duplicates:** if two modules share the same block of markup, CSS, or config shape, **one source of truth** + load/import — do not copy-paste with small drift.

**Exceptions:** truly trivial one-line literals; framework glue that must be inline; generated output under `temp/` (not source).

---

## 3. Method / function size

- A method or function should generally fit on **≤ about one screen / printed page** of substance (guideline **~40–80 lines**, matching existing pygetpapers guidance).
- **Exception:** long **cascading if/elif/else** or match chains that are clearer kept together than split artificially — still prefer extracting shared bodies and naming the cases.
- Prefer **small, well-named units** over monoliths; name after *what the unit does*.

---

## 4. Named constants for strings and numbers

- User-visible labels, status tokens (`include` / `exclude` / `review`), HTTP path fragments, file basenames, magic timeouts, retry counts, column names, and format codes belong in a **`constants` module** and/or **YAML/JSON config** — not scattered literals.
- Prefer **one vocabulary** across CLI, review table, and docs (same spelling and case).
- **Exceptions:** loop indices `i`/`j`, obvious `0`/`1` in tiny local math, and one-off test fixture strings that are the subject under test.

---

## 5. Suggested additions (for agreement)

These are proposed for this community (ECRs, personal branches, weekly review). Strike or edit before we lock the guide.

### 5.1 Product vs notebook

Short projects produce lots of scratch data; treating that like product code makes `main` unreadable and merges painful. Keep experiments on personal branches and promote only thin, reusable pieces.

- **`main` holds product code and thin docs.** Personal corpora, large XML/PDF dumps, videos, and zips stay on personal branches or outside git — see [branch_strategy_vs_prs.md](branch_strategy_vs_prs.md).
- Do not commit `__pycache__`, `.pyc`, secrets, or `.env` with credentials.

### 5.2 Fail loudly and specifically

Silent failures teach the wrong lesson in weekly review: people cannot tell whether the pipeline skipped, broke, or succeeded. Errors and tests should name the artefact and stage so mentors can diagnose quickly. Combined with **§0 No mocks**, a live outage must surface as skip/fail, not a green mock.

- Prefer clear exceptions / logged errors with **context** (path, PMCID, stage) over silent `pass` or bare `except:`.
- Tests use **`assert` with descriptive messages** (amilib rule) — not `return False`.

### 5.3 Pure-ish cores, I/O at the edges

Logic that only needs data structures is easy to unit-test and demo on a projector; network and disk are slow and flaky. Push downloads and writes to the boundary so the decision code stays reviewable.

- Separate **decide/transform** (easy to test) from **download/write** (needs network or disk).
- Pipeline stages should have **stable inputs/outputs on disk** where possible (BagIt / query dirs), so weekly review can inspect artefacts without running the whole stack.

### 5.4 Idempotent and resume-friendly

ECRs interrupt runs often (Ctrl-C, laptop sleep, rate limits). A step that can be re-run without trash or mystery duplicates saves hours and matches our pipeline tutorials.

- Re-running a step should **skip completed work** or overwrite safely with an explicit flag — not corrupt half-written trees.
- Document the **resume contract** next to the command (as in pipeline tutorials).

### 5.5 One vocabulary for IDs and paths

Review tables, bags, and docs must speak the same language or newcomers invent parallel fields. Pick one public spelling for each concept and map at the edges if an API disagrees.

- Use one convention for paper IDs (e.g. `PMC…`), packet paths, and review-table columns; document it once; do not invent parallel spellings (`pmcid` vs `PMCID` vs `pmc_id` in public APIs without mapping).

### 5.6 Accessibility and calm UX (when we ship HTML)

Our HTML is often opened locally by non-engineers during review. Expected empty results should look like normal outcomes, not crashes, and styling should live where designers can edit it.

- Prefer **external CSS**; avoid alarming defaults for expected failures (e.g. soft skip vs red panic for “no fulltext”).
- Interactive pages should work with a **local file** or simple static server where possible.

### 5.7 Comments and docs

The audience includes people new to the codebase every three months. Comments and dated docs should explain intent and provenance, not restate the next line of code.

- Comment **why** and non-obvious constraints; do not narrate obvious code.
- Tutorials and design notes use **system date of generation** and state date sources (existing rule).

### 5.8 Dependencies and licences

Every new package is a teaching and install burden on short-stay machines. Add libraries only when they clearly earn their keep, with a compatible licence and a known offline/online story.

- New dependencies need a one-line **why** and a licence compatible with the project (Apache-2.0 unless agreed otherwise).
- Prefer libraries that work **offline** or with clear network boundaries for ECR laptops.

### 5.9 AI-assisted edits

Generated code tends toward large inline blobs and opaque literals. Treat AI output like a junior patch: it must still meet these style rules and stay small enough to read in a weekly session.

- AI-generated code must still pass these rules: no giant inline HTML/CSS/JS; no mystery numbers; no new monolith files.
- Prefer **small diffs** the weekly review can read aloud.

---

## 6. Automatable checks

On branch workflows, run:

```bash
./venv/bin/python scripts/check_coding_style.py
./venv/bin/python scripts/check_coding_style.py --fix-path --fix-status   # safe rewrites
./venv/bin/python scripts/check_coding_style.py --check-markup              # report only
./venv/bin/python scripts/check_coding_style.py --check-long-functions      # report only
./venv/bin/python scripts/check_coding_style.py --check-mocks               # §0 mock/patch debt
./venv/bin/python scripts/check_coding_style.py --git-diff origin/main      # new corpora/temp
```

Default gate: Path comma-style, `sys.path` (unless marked), review-status constants. Markup extract, long-function splits, and mock sweep stay opt-in until debt is cleared.

---

## 7. How we will use this

1. **Agree** this document (edit §5 until it matches team practice).  
2. **Walk** hot paths (`corpus_review/`, `repositories/`, pipeline scripts, review HTML/CSS/JS) against the checklist below.  
3. **Record** exceptions in-file (`# style-exception: …`) or in a short appendix when a rule is deliberately broken.  
4. **Fix** high-value violations in small commits; do not boil the ocean in one PR/branch.

### Review checklist (print / share in session)

- [ ] **No mocks / patches / fake HTTP** in tests?  
- [ ] Could an OSS library do this?  
- [ ] Are JS / CSS / JSON / XML / templates external when humans edit them?  
- [ ] Are near-duplicate blocks consolidated?  
- [ ] Are functions roughly ≤ one page (except justified cascades)?  
- [ ] Are status strings and magic numbers named constants or config?  
- [ ] Absolute imports; no `sys.path`; empty `__init__.py` unless agreed?  
- [ ] No corpora/temp dumps / `__pycache__` headed for `main`?  
- [ ] Tests assert with clear messages?  

---

## Related

- [branch_strategy_vs_prs.md](branch_strategy_vs_prs.md)  
- [authors_202611.md](authors_202611.md)  
- pygetpapers / amilib style guides (links above)
