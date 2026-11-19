# Strategy — `repositories` submodule

**Status:** strategy outline only (**no implementation in this note**)  
**Date:** 2026-11-19  
**Module:** [`repositories`](overview.md) (`semantic_corpus.repositories`)  
**Owner focus:** Larisa Beni (+ Renu Kumari, Peter Murray-Rust as series co-authors)  
**Prompt:** [discussions/prompt_2026-11-19_repositories_strategy.md](../../../discussions/prompt_2026-11-19_repositories_strategy.md)  

**Related:** [south_asia.md](south_asia.md) · [../corpus/design.md](../corpus/design.md) · [../corpus/siblings.md](../corpus/siblings.md) · [../../joss_series_strategy.md](../../joss_series_strategy.md)

---

## 1. Purpose and boundary

### What `repositories` is for

Search and harvest **open scholarly repositories** (articles, theses, grey literature) with a **user-declared text query** (preferably **Boolean**) plus **date (and similar) constraints**, then hand results into the shared **`corpus` contracts** (stable IDs, documents, BagIt/review path).

### What it is not

| Not this | Belongs instead |
|----------|-----------------|
| BagIt filestore, cleaners, semantic HTML, review CRUD UI | **`corpus`** |
| Phrase/KG, encyclopedia content, chatbot UX | Sibling modules |
| Production IR operations | Out of scope |
| Hard-coded one-repo Python per new source forever | Anti-goal — see §3 |

Users should be able to **add a new repository by editing declarative files**, not by changing Python—except when a source needs a new *capability class* the generic engine cannot express yet (§3.3).

---

## 2. Relationship to `pygetpapers`

Much of the needed behaviour already exists in **[pygetpapers](https://github.com/petermr/pygetpapers)** (JOSS-published): multi-repo search, query flags, limits, download orchestration, config-ish workflows.

**Strategic stance:**

1. **Reuse concepts and proven flows** from pygetpapers (query → hit list → download → on-disk layout), including CLI familiarity already partially bridged via `semantic_corpus --pygetpapers`.  
2. **Do not fork pygetpapers into a second product.** Treat it as:
   - a **reference implementation** of repository search/download patterns, and/or  
   - an **optional upstream** whose output directories `corpus` already knows how to ingest, and/or  
   - a **source of declarative ideas** (per-repo parameters, boolean queries, limits).  
3. **Evolve `repositories` toward a declarative registry** that can drive the same *kinds* of operations pygetpapers does today in code, while feeding **`corpus` ingest hooks** as the preservation path.  
4. Where pygetpapers already supports a repository well (e.g. Europe PMC), prefer **thin adaptation + declaration** over rewriting search logic.  
5. Global South / thesis sources (SciELO, Redalyc, Shodhganga, …) may need **new declarative profiles** even when pygetpapers coverage is thin—still without inventing a parallel corpus layout.

**Success metric:** a researcher who knows pygetpapers queries can express the same intent in YAML (or equivalent) and land results in a `corpus` bag with skip-satisfied resume.

---

## 3. Declarative-first architecture (strategy)

### 3.1 User-visible artefacts

| Artefact | Role |
|----------|------|
| **Repository profile** | Describes one source: base URLs, query parameter mapping, Boolean dialect, date fields, auth/headers, pagination, rate hints, response shape, error vocabulary |
| **Query / pilot config** | What the *user* wants this run: which repo(s), query string, dates, limit *N*, formats, output/corpus target, timing verbosity |
| **Capability map** | Which *engine features* a profile may use (HTTP GET search, OAI-PMH, HTML list scrape, …)—profiles pick from a fixed set; new capability classes are rare and engineered |

Adding a repository ≈ **adding/editing a profile + example pilot**, then validating against live or fixture responses—not opening `europe_pmc.py` to copy-paste a sibling.

### 3.2 Shared query model (logical)

All profiles should map into a small **canonical query intent**:

| Field | Intent |
|-------|--------|
| `query` | Text search; **Boolean preferred** where the remote supports it (`AND` / `OR` / `NOT` / parentheses) |
| `date_from` / `date_to` (or equivalent) | Publication or index date window |
| `limit` / `page` / `cursor` | Bounded personal-corpus sampling; resume for next chunk |
| `formats` | What to fetch after hits (PDF, XML, landing HTML, …) |
| `repos` | One or more profile IDs |

Profiles declare **how** to translate this intent into wire requests (parameter names, date format, Boolean quirks). If a remote lacks Boolean, the profile documents **degraded mode** (e.g. simple string only) rather than silently inventing unsupported operators.

### 3.3 When Python *is* allowed

| Situation | Action |
|-----------|--------|
| New source fits existing capability (REST search + JSON hit list + PDF URL) | **Profile only** |
| New pagination or auth pattern still fits a documented capability | Extend **generic engine** once; many profiles reuse it |
| Truly novel protocol | New capability module + tests; still driven by profiles thereafter |
| One-off site breakage | Prefer profile tweak or recorded “server state” handler; avoid hard-coding site politics in call sites |

Legacy Python adapters already in-tree remain valid until migrated behind profiles; strategy is **convergence**, not big-bang delete.

### 3.4 Hand-off to `corpus`

`repositories` owns **find and fetch**.  
`corpus` owns **store, resume skip-satisfied, clean/semanticise, review UI**.

Strategy: every successful harvest ends by calling **corpus ingest hooks** (or writing a pygetpapers-compatible directory that corpus already ingests). Sibling schematic: dotted edge `repositories` -.-> `corpus`.

---

## 4. Server states and resilience

Remotes fail in structured ways. Strategy is to **classify, record, and act**—not crash with an opaque stack trace.

### 4.1 State model (illustrative)

| Class | Examples | Default policy (strategy) |
|-------|----------|---------------------------|
| **Success** | 200 + parseable hits | Continue; record timing |
| **Empty success** | 200 + zero hits | Stop that query branch; not an error |
| **Client / auth** | 401, **403**, 407 | Fail fast for that repo; surface “forbidden / blocked”; do not tight-loop retry |
| **Not found / gone** | 404 | Skip resource; continue siblings if multi-URL |
| **Rate / overload** | 429, 503 | Back off using profile `retry` / `Retry-After`; honour human limits |
| **Transient** | 408, 500, 502 | Limited retries with exponential backoff; then mark hit failed |
| **Payload unusable** | 200 but HTML interstitial / captcha / JSON schema drift | Treat as **blocked or profile stale**; log body fingerprint; do not pretend ingest succeeded |
| **Timeout / DNS** | network errors | Retry per profile; then abort run or skip repo per user policy |

**403** is explicitly a first-class example: often means User-Agent policy, geo/IP block, missing token, or scraping disallowed. Strategy: profiles carry UA/token requirements; diagnostics explain *likely* cause class; runs emit a **machine-readable status** per request (for resume and for JOSS/reproducibility notes).

### 4.2 Multi-repository runs

If one repository returns 403 and another 200, **do not fail the whole pilot** by default: record per-repo outcomes, ingest what succeeded, leave a clear report. User config may set `fail_fast: true` when preferred.

### 4.3 Human and limit stops

Aligned with `corpus`: runs are **stoppable**; reruns skip satisfied downloads. Repository layer must persist enough **cursor / offset / “already fetched ID”** state for that contract.

---

## 5. Timing and diagnostics (“if requested”)

Performance and blocking behaviour must be **observable** without turning every run into a debug dump.

### 5.1 What to measure (when timing requested)

| Metric | Why |
|--------|-----|
| DNS / connect / TTFB / total per request | Spot slow or hanging remotes |
| Search phase vs download phase | Separate query cost from full-text cost |
| Per-hit download times | Outliers, throttling |
| Backoff wait cumulative | True wall time vs active transfer |
| Hits returned vs limit | Whether the remote truncated early |

### 5.2 How users request it

Strategy: a **declarative switch** on the pilot (e.g. timing verbosity: off / summary / per-request) and/or a CLI flag. Default stays quiet; examples in docs show:

- a short **summary table** (repo, requests, median/p95 latency, status counts including 403), and  
- an optional **per-request log** for bug reports and JOSS reproducibility appendices.

### 5.3 Examples as documentation artefacts

Ship **recorded example timing summaries** (anonymised / fixture-based where possible) for EPMC and one slower GS or thesis source—so authors can cite “this is what a bounded run looks like” without implying SLA guarantees.

---

## 6. Query and date semantics (product rules)

1. Prefer **Boolean** queries when the profile says the remote supports them; document dialect differences (EPMC vs OpenAlex vs HTML sites).  
2. **Date constraints** are first-class in the canonical model; profiles map to the remote’s field (publish date, added date, etc.) and format.  
3. **Limits** are mandatory for personal corpora; “download everything matching” is not a default.  
4. **Multi-repo** pilots: same canonical query, per-profile translation; union of hits with clear provenance (`repo_id` + remote ID).  
5. **Degraded remotes** (no Boolean, no date filter): profile must declare unsupported fields; engine warns rather than inventing filters client-side unless a capability explicitly defines safe local filter-after-fetch (expensive; opt-in only).

---

## 7. Coverage roadmap (declarative profiles, not a claim of done)

| Tier | Examples | Notes |
|------|----------|--------|
| **A — pygetpapers-strong / already in tree** | Europe PMC, OpenAlex, arXiv | First profiles; timing examples; 403/UA lessons |
| **B — Latin America / GS (existing adapters)** | SciELO, Redalyc, CONICET, selected IRs | Migrate toward profiles; keep LA ownership narrative |
| **C — South Asia expansion** | **Shodhganga** (candidate), HEC PRR, JOL portals | See [south_asia.md](south_asia.md); volunteer + limits |
| **D — Bibliographic neighbour** | Zotero as *source*, not a remote search API twin | Interop via `corpus`; optional “export library” recipe |

JOSS text for this module should claim **declarative multi-repo search + resilient harvest into corpus**, with EPMC (and selected GS) as evidence—not an unbounded list of every IR on Earth.

---

## 8. Testing and quality bar

- **No mocks** for claimed harvest behaviour; real fixtures + gated live tests (`SC_LIVE_API=1`).  
- Fixture set per profile: sample search response, sample error bodies (**403** page/JSON), one successful full-text fetch.  
- Contract tests: profile → canonical query → recorded wire expectations (without live net in CI).  
- Resume tests: second run skips IDs already in corpus.  
- Timing tests: optional, assert that summary fields are present when timing is on—not that absolute latencies meet a number.

---

## 9. Docs, CLI, and user journey

1. **Pilot YAML** + short tutorial: Boolean query + date window + limit + one repo.  
2. **Add-a-repo guide**: copy a Tier A profile, change URLs/params, run against a fixture, then a live limited query.  
3. **Diagnostics guide**: how to read 403 vs 429 vs schema drift; how to turn on timing.  
4. CLI remains thin: point at pilot config; optional `--pygetpapers` bridge until declarative path is primary.  
5. Weekly submodule meetings (Larisa + PMR) own profile reviews and partnership outreach.

---

## 10. Risks and open decisions

| Risk / decision | Strategy note |
|-----------------|---------------|
| Profile language expressiveness vs complexity | Start small (HTTP search + pagination + download URL template); grow capabilities deliberately |
| Boolean dialect mismatch | Explicit profile flags; warn on unsupported operators |
| Legal / ToS / scraping | Prefer official APIs; HTML only with limits, UA honesty, and stop-on-403 |
| Overlap with pygetpapers maintenance | Coordinate; semantic_corpus consumes and declares, does not silently diverge forever |
| Shodhganga / thesis APIs | Confirm access before promising; limited pilots only |
| Auth secrets | Profiles reference env vars / secret names—never commit tokens |

---

## 11. Phased delivery (no code here—ordering only)

| Phase | Outcome |
|-------|---------|
| **0** | This strategy + inventory of current Python adapters vs pygetpapers coverage |
| **1** | Canonical query model + profile schema (documented); EPMC as reference profile |
| **2** | Engine behaviours: status classes, backoff, multi-repo partial success, timing summary |
| **3** | Hand-off to `corpus` ingest hooks + skip-satisfied IDs |
| **4** | Migrate 1–2 existing GS adapters to profiles; docs “add a repository without Python” |
| **5** | Optional Shodhganga / South Asia pilot profile if access and volunteer allow |
| **6** | JOSS paper draft for `repositories` citing declarative design + resilience + corpus interop |

---

## 12. One-sentence strategy claim

**`repositories` becomes a declarative, pygetpapers-informed multi-source search/harvest layer—Boolean and date-aware, resilient to HTTP realities such as 403, optionally timed, and always ending in `corpus` contracts—so new repositories are added as data, not as new Python modules.**
