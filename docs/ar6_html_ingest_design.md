# Design: Declarative AR6 WG*/SYR HTML download & clean

**Date:** 2026-11-10  
**Status:** design (no implementation in this doc)  
**Scope:** IPCC **AR6 WG1, WG2, WG3, and SYR** online HTML only. **Omit** Special Reports (SR15 / SROCC / SRCCL) for now.  
**Related:** [pipeline.md](pipeline.md) · [pipeline_kg_mappers.md](pipeline_kg_mappers.md) · existing lineage in `amilib` / `amiclimate` / `pyamihtml` (reference only)

---

## 1. Goal

Produce **clean, sectioned HTML with stable IDs** for AR6 working-group and synthesis report components (chapters, SPM, TS, cross-chapter papers, and HTML annexes where the web page is the text source), so the team and community can consume the same artifacts without bespoke per-site Python.

**Non-goals (this design):**

- SR* WordPress reports (later: another collection pack)
- PDF-primary annex/glossary pipelines (separate path; see §8)
- Full `semantic_corpus` phrase/KG pipeline (consumes the HTML later via `--source`)

---

## 2. Design principles

1. **Declarative first** — inventories, URL templates, fetch policy, clean profiles, and ID rules live in data (YAML/JSON), not in `if report == "wg1"` code.
2. **Named profiles, not site classes** — “Gatsby” / “WordPress” become **publisher/clean profiles** referenced by name; detection can choose a profile, code does not hardcode IPCC XPaths.
3. **Doit-like stages** — each component × stage is skip-if-done; force remake is explicit.
4. **Polite fetch** — rate limits, retries, timeouts, User-Agent, robots awareness; never hang forever (contrast pygetpapers).
5. **HTML is the product** — community deliverable is readable, linkable HTML (`html_with_ids.html` or equivalent), plus provenance sidecar.
6. **Open Source extractors as plugins** — prefer Trafilatura / Readability as fallbacks; use declared CSS/XPath main-content roots when fidelity matters.

---

## 3. High-level pipeline (doit-like)

Per **component** (e.g. `ar6.wg1.chapter-03`, `ar6.syr.spm`):

```text
manifest ──► resolve URLs
                │
                ▼
         [1] fetch          → raw.html (+ headers.json)
                │
                ▼
         [2] detect         → publisher profile name (optional override in manifest)
                │
                ▼
         [3] clean          → clean.html   (cruft off; main content kept)
                │
                ▼
         [4] structure      → structured.html  (normalise headings / sections)
                │
                ▼
         [5] add_ids        → html_with_ids.html (+ id_list.json)
                │
                ▼
         [6] validate       → report (coverage, empty body, missing h1, …)
                │
                ▼
         publish / hand off → community tree + provenance
```

**Global / batch tasks** (also doit-style):

| Task | Role |
|------|------|
| `manifest_check` | Schema-validate collection pack; expand chapter ranges |
| `status` | Which components are at which stage |
| `fetch_all` / `ensure --target add_ids` | Batch ensure |
| `coverage` | Compare disk vs expected components from manifest |

Skip-if-done keys: content hash of inputs + profile version + stage name (same idea as pipeline stamps).

---

## 4. Declarative collection pack

One pack per collection (first pack: `ipcc-ar6`). Nothing IPCC-specific in the engine—only in the pack.

### 4.1 Sketch (illustrative)

```yaml
collection:
  id: ipcc-ar6
  title: IPCC AR6 Working Groups + SYR
  license_note: "IPCC material; respect site ToS and attribution"

fetch:
  user_agent: "semantic_corpus-ar6-ingest/0.1 (+https://github.com/semanticClimate/semantic_corpus)"
  timeout_s: 60
  max_retries: 3
  backoff_s: [2, 5, 15]
  rate_limit_per_host: 0.2   # ~1 request / 5 s
  prefer: [httpx, playwright]  # try static first; escalate if body too thin

profiles:
  gatsby_report:
    detect:
      any_of:
        - meta: { name: generator, contains: "Gatsby" }
        - selector_exists: "#___gatsby"
        - script_src_contains: "gatsby"
    clean:
      strategy: main_selector_then_extractor
      main_selectors:
        - "main"
        - "article"
        - "[data-testid='chapter-content']"   # example; real selectors live only in pack
      drop_selectors:
        - "nav"
        - "header"
        - "footer"
        - "[role='navigation']"
        - ".cookie"
        - "aside"
      extractor_fallback: [trafilatura, readability]
      keep: [h1, h2, h3, h4, h5, h6, p, ul, ol, li, table, thead, tbody, tr, th, td,
             figure, figcaption, img, blockquote, section, div]
  # wordpress_report: omitted for AR6 WG*/SYR scope (used later for SR*)

id_rules:
  default:
    heading_pattern: "auto"          # prefer existing section numbers in heading text
    paragraph_id: "{section}.{n}"    # or sequential under section
    spm_lettered: true               # A.1, B.2 style when detected

components:
  - id: ar6.wg1.chapter-01
    kind: chapter
    report: wg1
    source:
      kind: html
      url: "https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-1/"
    profile: auto                    # or force: gatsby_report
    out_dir: "wg1/Chapter01"

  - id: ar6.wg1.spm
    kind: spm
    report: wg1
    source:
      kind: html
      url: "https://www.ipcc.ch/report/ar6/wg1/summary-for-policymakers/"
    profile: auto
    out_dir: "wg1/summary-for-policymakers"

  # … WG2/WG3 chapters, TS, CCP*, SYR longer-report / SPM / TS …
```

**Expansion helpers** (declarative, not hardcoded loops in callers):

```yaml
generate:
  - report: wg1
    kind: chapter
    range: [1, 12]
    url_template: "https://www.ipcc.ch/report/ar6/wg1/chapter/chapter-{n}/"
    id_template: "ar6.wg1.chapter-{n:02d}"
    out_dir_template: "wg1/Chapter{n:02d}"
```

The engine expands `generate` → concrete `components`. URLs live **only** in the pack.

### 4.2 What must not be in engine code

- Absolute IPCC paths (`/report/ar6/wg1/...`)
- “If Gatsby then strip `#___gatsby`” as IPCC-named classes
- Fixed chapter counts for WG1=12, WG2=18, …
- Cleaner XPaths bound to `IPCCGatsby` types

Engine APIs take: `url`, `profile`, `fetch_policy`, `id_rules`.

---

## 5. Stage details

### Stage 1 — Fetch (polite scrape)

**Input:** component `source.url` (+ optional `url_candidates`).  
**Output:** `raw.html`, `fetch_meta.json` (status, final URL, timing, tool used).

**Behaviour:**

1. Honour `rate_limit_per_host`, timeout, retries.
2. Try **static HTTP** (`httpx`/`requests`) first.
3. If body is below `min_bytes` or matches “shell only” heuristics (declared in profile), escalate to **Playwright** (preferred over Selenium for modern automation) to get post-JS DOM HTML.
4. Never use infinite timeout; record failures in a run log (same spirit as EPMC HTTP tallies).

**Open Source tools:**

| Role | Recommendation |
|------|----------------|
| HTTP | `httpx` or `requests` |
| JS render | **Playwright** (primary), Selenium (legacy ok) |
| Crawl framework | Scrapy **not** required for a fixed inventory |

**Scrape surface (declared):**

- Default: full document HTML after render.
- Optional pack fields: `wait_for_selector`, `remove_before_save` (cookie banners), `include_frames: false`.
- Do **not** scrape site chrome into the long-term artifact; that is Stage 3’s job—but saving full `raw.html` preserves provenance.

### Stage 2 — Detect authoring system

**Input:** `raw.html`.  
**Output:** `profile` name + confidence.

**Signals** (all declarative in `profiles.*.detect`):

- `<meta name="generator" content="Gatsby …">`
- DOM markers (`#___gatsby`, `__NEXT_DATA__`, WordPress theme classes, etc.)
- Script `src` substrings

If manifest sets `profile: gatsby_report`, skip detection.  
If `auto` and no match → use pack `default_profile` or `extractor_only` (Trafilatura-only clean).

**Informational:** detection is for choosing a **clean profile**, not for branching business logic in code.

### Stage 3 — Remove website cruft

**Input:** `raw.html` + resolved profile.  
**Output:** `clean.html` (still HTML).

**Strategy cascade** (profile-driven):

1. **`main_selector`** — keep first matching subtree (highest fidelity for IPCC chapter structure).
2. **`drop_selectors`** — delete nav/footer/cookie/aside/ads.
3. **Extractor fallback** (Open Source):
   - **[Trafilatura](https://github.com/adbar/trafilatura)** — best general main-content extraction; keep as HTML/XML when possible; strong public benchmarks vs Readability / jusText / boilerpy3.
   - **[readability-lxml](https://github.com/buriy/python-readability)** — Mozilla/Arc90 reader-mode; good second fallback.
   - **jusText** / **boilerpy3** — optional further fallbacks; often worse at preserving heading/figure structure.

**Important:** generic extractors can flatten or drop nested IPCC section wrappers. For AR6 WG* chapters, **declared main selectors should win** when they match; Trafilatura is the safety net and the default for unknown hosts.

Allowlist tags/attributes in the profile (`keep`, `keep_attrs`) so community HTML stays simple.

### Stage 4 — Structure (semantic HTML normalisation)

**Input:** `clean.html`.  
**Output:** `structured.html`.

- Promote consistent heading hierarchy where safe.
- Wrap loose blocks into `<section>` when rules say so.
- Normalise figures: `figure` + `figcaption` when caption pattern matches (declarative regexes in pack).
- Resolve or preserve relative image URLs (policy in pack: `images: rewrite_to_absolute | leave | drop`).

No IPCC-specific Python—only rule tables.

### Stage 5 — Sectioning with IDs

**Input:** `structured.html` + `id_rules`.  
**Output:** `html_with_ids.html`, `id_list.json` (and optionally `para_list.html` for humans).

**Rules (data):**

- Prefer numbers already in headings (`3.1.2`, SPM `A.1`).
- Assign stable `id` on `section` / `h*` / `p` as configured.
- Collision policy: suffix `-2`, `-3` or fail validate.
- Do not invent IPCC curly-ref rewriting in the engine unless expressed as pack transforms (`link_rewrite` rules).

This stage is what makes the HTML **consumable** for search, annotation, and later packet indexing in `semantic_corpus`.

### Stage 6 — Validate

**Checks (configurable thresholds):**

- Body text length / paragraph count minima  
- At least one `h1` or title  
- ID uniqueness  
- Optional: share of paragraphs with IDs  
- Optional: warn if `clean.html` ≈ size of `raw.html` (cleaner no-op)

Failures do not delete prior stage outputs; status registry records `validate=fail` with reasons.

---

## 6. Doit-like task graph (batch view)

```text
manifest_check
      │
      ▼
fetch:ar6.wg1.chapter-01 ──► detect:… ──► clean:… ──► structure:… ──► add_ids:… ──► validate:…
fetch:ar6.wg1.chapter-02 ──► … (parallelism capped by rate_limit)
…
fetch:ar6.syr.spm ──► …
      │
      ▼
coverage / publish
```

**Targets people run:**

```text
ensure add_ids --report wg1
ensure validate --collection ipcc-ar6
ensure publish --outdir corpora/ipcc_ar6_html
```

Implementation may use **doit** (as in `semantic_corpus` pipeline) or the existing `ar6_processor` registry pattern—same semantics: stage stamps + force.

---

## 7. Community / team deliverable layout

Suggested output tree (BagIt-friendly later):

```text
corpora/ipcc_ar6_html/
  collection.yaml                 # copy or pointer to pack used
  provenance.json                 # tool versions, profile versions, run time
  wg1/
    Chapter01/
      raw.html                    # optional in “release” builds; keep in “work” builds
      clean.html
      html_with_ids.html          # ★ primary hand-off
      id_list.json
      fetch_meta.json
    summary-for-policymakers/
      …
  wg2/ …
  wg3/ …
  syr/ …
```

**Release profile:** ship `html_with_ids.html` + `id_list.json` + `collection.yaml` + `provenance.json` (omit bulky `raw.html` unless requested).

Consumers: annotation tools, encyclopaedia/KG later, human readers, `semantic_corpus --source` ingest.

---

## 8. PDF note (out of band for this HTML design)

Some AR6 components are PDF-primary (many annexes/glossaries) or need PDF for **figures** / Docling text. That remains a **parallel declarative path**:

- `source.kind: pdf` with `pdf: required | lazy | on_demand`
- Not mixed into Stages 1–5 above except as an explicit alternate component entry

This HTML design does not download PDFs unless a component declares them for figures/display sidecars.

---

## 9. Mapping from today’s bespoke stack

| Today (amilib / amiclimate) | This design |
|-----------------------------|-------------|
| `EXPECTED_COMPONENTS` / missing lists in Python | `components` + `generate` in pack |
| `IPCCGatsby` / `IPCCWordpress` classes | Named `profiles` + detect rules |
| Hardcoded `AmiDriver` `chapter/{chap}` URLs | Per-component / templated URLs in pack |
| Ad-hoc clean XPaths in Python | `main_selectors` / `drop_selectors` / extractor fallback |
| `ar6_processor` stages download→clean→structure→add_ids | Same stages; registry driven by pack |
| Empty `ar6_processor/config/` | Becomes the home for packs + profiles |

Reuse processors; stop growing IPCC-named code paths.

---

## 10. Open Source scraper / cleaner summary

| Need | Prefer | Why |
|------|--------|-----|
| Static get | httpx / requests | Simple, timeout-safe |
| JS pages | Playwright | Reliable post-hydrate HTML |
| Main content fallback | **Trafilatura** | Best general quality/benchmarks; structured output options |
| Second fallback | readability-lxml | Reader-mode subtree |
| Site-precise keep | CSS/XPath in pack | Preserves IPCC section DOM for IDs |

Avoid building a permanent custom “IPCC Gatsby cleaner” in code; express the same selectors in the pack and keep OSS extractors as fallback.

---

## 11. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| IPCC redesign breaks selectors | Profile version pin; detect confidence; Trafilatura fallback; golden HTML fixtures in CI |
| Playwright blocked / slow | Rate limit; cache `raw.html`; resume by stage |
| Extractor drops figures/tables | Prefer `main_selector`; allowlist `figure`/`table`; validate figure count vs raw |
| Over-scraping | Fixed inventory only (no open crawl); polite defaults |
| ID instability across runs | Rules version in provenance; prefer heading-derived IDs |

---

## 12. Suggested implementation order (later)

1. Pack schema + `manifest_check` + expand `generate` for WG1 chapters only.  
2. `fetch` (httpx → Playwright) with timeouts/rate limit.  
3. `detect` + one `gatsby_report` profile using selectors + Trafilatura fallback.  
4. `add_ids` + `validate` for one chapter golden test.  
5. Expand pack to WG2/WG3/SYR; batch `ensure add_ids`.  
6. Wire output directory to `semantic_corpus --source` (separate design).

---

## 13. Success criteria

- No IPCC URL or Gatsby XPath in engine source—only in `ipcc-ar6` pack data.  
- Re-run is mostly no-ops (stage skip-if-done).  
- Community can open `html_with_ids.html` and see numbered sections with stable anchors.  
- Swapping cleaner to Trafilatura-only is a pack/profile edit, not a code fork.
