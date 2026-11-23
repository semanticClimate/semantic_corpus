# Submodule guidelines — corpus-owned interface contract

**Date:** 2026-11-20  
**Owner:** `corpus/` (core; defines interfaces for all submodules)  
**Audience:** owners of `repositories`, `phrases_kg`, encyclopedia/chatbot bridges, and future modules  
**Status:** normative draft — weekly meeting accepts changes  
**Prompt:** [discussions/prompt_2026-11-20_submodule_guidelines.md](../../../discussions/prompt_2026-11-20_submodule_guidelines.md)  
**Related:** [`MODULE_SPEC.md`](../../MODULE_SPEC.md) · [team_interop_governance.md](team_interop_governance.md) · [coding_style.md](../../../docs/coding_style.md) · [branch_strategy_vs_prs.md](../../../docs/branch_strategy_vs_prs.md) · [modules/README.md](../../../docs/modules/README.md)

**Principle:** submodules implement **against** contracts published by `corpus/`. They may add domain behaviour (adapters, phrases, UI) but must not invent parallel BagIt layouts, paper-ID spellings, review-table columns, or ingest dialects. Social parallel: [team_interop_governance.md](team_interop_governance.md) (guidelines → validate → harvest).

---

## 0. Checklist at a glance

| Area | Must have |
|------|-----------|
| Layout | `module.yaml`, `README.md`, `docs/`, public `__init__` per [`MODULE_SPEC.md`](../../MODULE_SPEC.md) |
| Docs | Package `docs/` + JOSS overview under `docs/modules/<name>/` |
| Tests | Real fixtures; no mocks; offline by default; live gated |
| Launcher | CLI entry usable from Streamlit/GUI without duplicating logic |
| Ops code | Pure-ish core; I/O at edges; resume / skip-satisfied |
| Quality | [coding_style.md](../../../docs/coding_style.md); `check_coding_style.py` |
| CI/CD | Module tests green on PR; style gate; no secrets in git |
| YAML | Pilots / profiles declarative; schema-documented; no magic in Python |
| Branches | Named contributor branches; thin product on `main` |
| Interfaces | Honour corpus BagIt, IDs, review columns, ingest hooks |

---

## 1. Documentation

### 1.1 Required surfaces

| Surface | Location | Content |
|---------|----------|---------|
| Package short README | `semantic_corpus/<name>/README.md` | Purpose, owner, how to run one demo |
| Module docs | `semantic_corpus/<name>/docs/` | Source lists, local design, adapter notes |
| JOSS / series overview | `docs/modules/<name>/overview.md` | In/out of scope, contracts, one-liner |
| Design / strategy (as needed) | `docs/modules/<name>/` or package `docs/` | Non-trivial behaviour; keep dated |
| Prompt archive | `discussions/prompt_YYYY-MM-DD_*.md` | Verbatim prompts that drove doc/code |

### 1.2 Rules

1. **`module.yaml` `docs` field** must point at the JOSS overview and stay in sync with the package name.  
2. Document **public contracts** (IDs, paths, CLI flags, YAML keys) once; link elsewhere—do not drift spellings.  
3. Prefer **short runnable demos** in docs (limit-N, offline fixture) over prose-only claims.  
4. Use **system date of generation** on new design notes; state date sources.  
5. Cross-module claims belong in `docs/modules/` or `corpus/docs/`; domain lists (e.g. LA sources) stay in the submodule’s `docs/`.

---

## 2. Tests

### 2.1 Norms

| Rule | Detail |
|------|--------|
| **No mocks** | No `unittest.mock` / patches of production collaborators ([coding_style.md](../../../docs/coding_style.md) §0) |
| **Real fixtures** | Small XML/PDF/JSON/HTML under `tests/resources` (or module-equivalent) |
| **Offline default** | CI and local `pytest` must pass without network |
| **Live API** | Mark `live_api` / `network`; require `SC_LIVE_API=1`; skip/fail clearly on outage |
| **Assert messages** | `assert …, "context"` naming path, ID, stage |
| **Contract tests** | Assert submodule outputs satisfy **corpus** layout / ID / review vocabulary |

### 2.2 What every submodule should cover

1. At least one **happy-path** test from declarative input → on-disk artefact.  
2. At least one **resume / skip-satisfied** or idempotent re-run where the module writes trees.  
3. At least one **boundary** test: invalid YAML, empty hits, or HTTP empty-success (as applicable)—without mocking the collaborator away.  
4. No committed corpora dumps or `__pycache__`.

---

## 3. Code

### 3.1 Launcher (CLI and GUI)

| Requirement | Detail |
|-------------|--------|
| **Thin CLI** | Entry points parse args / load YAML, then call a **library API** |
| **GUI-safe API** | Same functions callable from Streamlit (or similar) without `sys.argv` parsing inside ops code |
| **One vocabulary** | Flag names, YAML keys, and GUI labels share spellings with docs |
| **Exit / return** | CLI exits with clear codes; library returns structures or raises typed errors—no `sys.exit` deep in ops |
| **Demo flag pattern** | Support limit-N / dry-run / reuse-existing where network or volume is costly |

Do **not** put business logic only in `__main__` or Streamlit widgets.

### 3.2 Operational code

1. **Depends on corpus contracts** unless the module *is* `corpus` ([`MODULE_SPEC.md`](../../MODULE_SPEC.md) Rules).  
2. Separate **decide/transform** from **download/write** ([coding_style.md](../../../docs/coding_style.md) §5.3).  
3. Stages leave **inspectable artefacts** on disk (BagIt / query dirs / review rows).  
4. Prefer **idempotent / resume-friendly** behaviour (§5.4).  
5. Fail **loudly and specifically** (path, PMCID/ID, stage)—no bare `except:` / silent `pass`.  
6. Absolute imports; no `sys.path` hacks; empty `__init__.py` unless agreed.  
7. Prefer existing OSS; new deps need a one-line why + compatible licence.

### 3.3 Code quality

| Gate | Tool / doc |
|------|------------|
| Style | [coding_style.md](../../../docs/coding_style.md) |
| Automatable | `scripts/check_coding_style.py` (Path, mocks, long functions as enabled) |
| Size | Functions ~≤ one screen; no giant inline HTML/CSS/JS |
| Constants | Status strings, columns, timeouts in `constants` or YAML |
| AI patches | Small diffs; still must pass these rules (§5.9) |

### 3.4 CI/CD

| Expectation | Detail |
|-------------|--------|
| **PR / branch** | Lint + submodule-relevant pytest green before merge to `main` |
| **Secrets** | No API keys, `.env` with credentials, or tokens in git |
| **Artefacts** | CI must not require large personal corpora; use fixtures |
| **Live jobs** | Optional / manual or scheduled; never the only proof of correctness |
| **Install story** | Honour `python_extra` in `module.yaml` (optional deps stay optional) |

Current baseline workflow: [`.github/workflows/lint.yml`](../../../.github/workflows/lint.yml). Extend coverage module-by-module; do not weaken the no-mock / offline default.

---

## 4. Declarative files (YAML / JSON)

### 4.1 What belongs in YAML

| Prefer declarative | Examples |
|--------------------|----------|
| Query pilots | Topic, limit, date window, source id |
| Per-source profiles | Capability flags, endpoints, timing verbosity |
| Schemas / manifests | Review columns, facility lists (`module.yaml`) |
| Label lists | Controlled vocabularies exposed to users |

### 4.2 Rules

1. Humans who are **not** Python maintainers must be able to add a pilot by editing YAML when the capability class already exists.  
2. Document **keys and enums** next to examples (`docs/modules/<name>/declarative_*.md` or package `docs/`).  
3. Validate early; reject unknown keys or warn loudly—do not ignore silently.  
4. Do not bury the same config as string literals in `.py` ([coding_style.md](../../../docs/coding_style.md) §2).  
5. Pilots used in demos and CI must be **small** (limit-N) and checked in under `config/` or `tests/resources/`.

---

## 5. Project management

### 5.1 Branches

| Practice | Detail |
|----------|--------|
| **Named branches** | Prefer long-lived contributor/theme branches for JOSS credit ([joss_series_strategy.md](../../../docs/joss_series_strategy.md)) |
| **`main` is product** | Thin code + docs; no personal corpora, bulk PDF/XML, videos ([branch_strategy_vs_prs.md](../../../docs/branch_strategy_vs_prs.md)) |
| **Interface changes** | PRs that change corpus contracts need weekly-meeting acceptance before advertise in JOSS |
| **Authors map** | Keep people ↔ branches ↔ themes in `docs/authors_*.md` |

### 5.2 Testing as process

1. Owners run **offline pytest** for their module before asking for harvest into `main`.  
2. Weekly review can demand a **projector demo** (CLI or GUI) from a checked-in pilot.  
3. Live API demos are evidence, not a substitute for fixture tests.  
4. Failures in review are fixed on the branch; do not “merge and hope.”

### 5.3 Ownership

| Role | Duty |
|------|------|
| **Focus owner** (`module.yaml` `owner`) | Docs, tests, demos, branch hygiene for that module |
| **`corpus/` hub** | Interface definitions, acceptance of contract changes |
| **Co-authors** | Usually Renu + PMR on papers; listed in `module.yaml` |

---

## 6. Additional necessary components

These are required for a dispersed, AI-assisted team and for JOSS-quality interop—not optional polish.

### 6.1 Public interfaces and import boundaries

- Stable **paper IDs**, BagIt/workdir layout, review-table columns, ingest hooks, semantic HTML chunk IDs—owned by `corpus/`.  
- Submodules **consume** those types/paths; they do not redefine them.  
- Prefer package imports that make illegal dependencies visible (future: import-linter or equivalent).

### 6.2 Error, HTTP, and empty-result semantics

- Distinguish **transport failure**, **auth/forbidden**, **empty success** (zero hits), and **partial download**.  
- Document per-source behaviour in module docs (see repositories strategy / declarative controls).  
- Expected empty results must be calm in CLI/GUI—not a red panic.

### 6.3 Logging and timing

- Log **stage + artefact id**; optional declarative timing verbosity for slow sources.  
- Default quiet enough for demos; verbose enough for mentoring.

### 6.4 Provenance, licensing, and data placement

- Record enough provenance to re-run or cite (source, query, date, tool version where practical).  
- Respect upstream licences/access; do not commit copyrighted bulk full text to `main`.  
- Runtime corpora live under agreed workdirs (`corpora/`, BagIt trees)—not scattered temp dumps on `main`.

### 6.5 Dependencies and install extras

- Declare optional stacks via `python_extra` / extras (`[kg]`, streamlit, etc.).  
- Core install must not force every submodule’s heavy deps.

### 6.6 Resources and recorded fixtures

- Checked-in **bytes** (JSON/XML/PDF samples) beat mocks.  
- Keep fixtures tiny; document which live endpoint they came from.

### 6.7 Demo and reproducibility pack

- Every submodule ships **one** documented limit-N (or offline) demo command.  
- Demo YAML + expected artefact shape belong in docs or `config/`.

### 6.8 Secrets and credentials

- Env vars / local config only; document required names in README.  
- Never commit credentials; CI uses repository secrets only when essential.

### 6.9 Internationalisation / non-English sources

- Submodules that touch Global South / non-EN corpora document encoding, language metadata, and access constraints.  
- Do not assume Europe PMC–like APIs exist for every source.

### 6.10 AI-assisted contribution disclosure

- Archive prompts that drove design under `discussions/`.  
- AI output is a patch: must pass style, tests, and interface rules before harvest.

### 6.11 Versioning and changelog discipline

- Interface-breaking changes to corpus contracts are **explicit** (ADR or dated note + meeting acceptance).  
- Submodule READMEs note when they require a newer corpus contract.

### 6.12 Accessibility of HTML/GUI

- External CSS/JS; usable as local file or simple server where practical ([coding_style.md](../../../docs/coding_style.md) §5.6).  
- Streamlit/GUI is a launcher over the library API—not a second implementation.

---

## 7. Acceptance gate (“harvest”)

Before submodule work lands on `main` or is advertised for JOSS:

1. [ ] Layout + `module.yaml` complete  
2. [ ] Docs: README + package `docs/` + overview link  
3. [ ] Offline tests green; no new mocks  
4. [ ] CLI and/or GUI call the **same** library API  
5. [ ] Declarative pilot checked in and documented  
6. [ ] Honour corpus interfaces (IDs, BagIt, review columns)  
7. [ ] Style check / CI green  
8. [ ] No secrets or bulk corpora on the merge path  
9. [ ] Interface changes accepted in weekly meeting if contracts changed  

---

## 8. One sentence

**`corpus/` publishes the interfaces; every submodule documents, tests, launches (CLI/GUI), configures (YAML), and branches against those interfaces—validated automatically, then harvested—same order as COAR / OpenAIRE-style guidelines-then-harvest.**
