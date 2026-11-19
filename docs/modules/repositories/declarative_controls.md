# Declarative controls — EPMC, CONICET, Shodhganga

**Module:** [`repositories`](overview.md)  
**Targets:** [target_examples.md](target_examples.md) · **Strategy:** [strategy.md](strategy.md)  
**Prompt:** [discussions/prompt_2026-11-19_repositories_declarative_controls.md](../../../discussions/prompt_2026-11-19_repositories_declarative_controls.md)  
**Status:** specification / teaching sketches (**not** shipped profile files yet)

Two layers of declaration:

1. **Pilot config** — what the user wants this run (shared schema across sites).  
2. **Repository profile** — how that intent maps onto a remote (per site; add a repo by editing this, not Python).

---

## 1. Shared pilot controls (canonical)

Used in every target pilot (same keys; profiles interpret them):

| Control | Type | Meaning |
|---------|------|---------|
| `query_name` | string | Short label for the run / corpus |
| `repository` | string | Profile id: `europe_pmc` \| `conicet` \| `shodhganga` |
| `query_string` | string | Text search; **Boolean preferred** where the profile allows |
| `limit` | int | Max hits this run (personal-corpus bound) |
| `start_date` | date `YYYY-MM-DD` or null | Inclusive lower bound (if profile supports dates) |
| `end_date` | date `YYYY-MM-DD` or null | Inclusive upper bound (if profile supports dates) |
| `formats` | list | e.g. `pdf`, `xml`, `html`, `metadata` |
| `corpus_name` / `output_subdir` | string | Hand-off into `corpus` / on-disk layout |
| `timing` | `off` \| `summary` \| `per_request` | Optional latency diagnostics |
| `fail_fast` | bool | If true, abort multi-step run on first hard error (e.g. 403) |
| `user_agent` / `headers_env` | optional | Only if profile requires; secrets via env names, not literals |

Existing EPMC-style pilots in `config/*.yaml` already use most of the query/limit/date/formats keys.

---

## 2. Per-site profile controls

### 2.1 Europe PMC (`europe_pmc`)

| Profile control | Declarative intent | Notes (today → target) |
|-----------------|--------------------|-------------------------|
| `capability` | `rest_json_search` | Official search API |
| `base_url` | EPMC REST root | e.g. search endpoint under europepmc.org |
| `query_param` | `query` | Full string sent to API |
| `boolean` | `native` | EPMC Boolean (`AND`/`OR`/`NOT`, fields like `HAS_FT:Y`) |
| `date_mode` | `embed_in_query` | Engine wraps with `FIRST_PDATE:[from TO to]` when dates set |
| `date_field` | `FIRST_PDATE` | Publication date window |
| `page_size_param` | `pageSize` | Capped (remote max 1000; pilots use small `limit`) |
| `result_type` | `core` | Metadata richness |
| `formats_map` | `pdf`, `xml`, … | Download paths after hit list |
| `http_states` | map 403/429/5xx → policy | UA / rate-limit classes; no tight retry on 403 |
| `timing_hooks` | search vs download phases | For `timing: summary` |

**Pilot sketch (normal):**

```yaml
query_name: epmc_heatwaves_demo
repository: europe_pmc
query_string: '("marine heatwave" OR "ocean heatwave") AND (HAS_FT:Y)'
limit: 20
start_date: "2020-01-01"
end_date: "2026-12-31"
formats: [xml, pdf]
timing: summary
corpus_name: epmc_heatwaves_demo
```

**Smoke / slow-network example (`limit: 2`):** [`config/epmc_limit2_demo.yaml`](../../../config/epmc_limit2_demo.yaml)

```yaml
query_name: epmc_limit2_demo
repository: europe_pmc
query_string: '("marine heatwave" OR "ocean heatwave") AND (HAS_FT:Y)'
limit: 2
start_date: "2020-01-01"
end_date: "2026-12-31"
formats: [xml, pdf]
timing: summary
corpus_name: epmc_limit2_demo
```

```bash
./venv/bin/python scripts/build_example_corpus.py \
  --config config/epmc_limit2_demo.yaml
```

**Rerun:** the same command with `limit: 2` skips papers already on disk and downloads **2 new** ones (then ingests them). Do **not** pass `--reuse-existing` if you want new papers.

If Europe PMC returns **503** (temporary nginx outage), wait and retry, or reuse the last successful query dir (no new downloads):

```bash
./venv/bin/python scripts/build_example_corpus.py \
  --config config/epmc_limit2_demo.yaml \
  --reuse-existing
```

(Aligned with `config/ocean_heatwaves_2026.yaml` for larger runs.)

---

### 2.2 CONICET (`conicet`)

| Profile control | Declarative intent | Notes (today → target) |
|-----------------|--------------------|-------------------------|
| `capability` | `html_ir_search` | DSpace-style HTML search + item pages (in-tree scraper) |
| `base_url` | CONICET Digital site root | Institutional IR |
| `search_path` / `search_url` | Simple search endpoint | `query` + `rpp` style params today |
| `query_param` | `query` | Free text |
| `boolean` | `degraded` \| `strip_wrapper` | Today: wrappers like quotes/`()` stripped; **not** full EPMC Boolean—profile must declare this |
| `date_mode` | `unsupported` → later `local_filter` or remote if discovered | **Today dates are ignored** in adapter; declarative profile should warn if pilot sets dates |
| `rpp` / page size | min(limit, site cap) | e.g. cap 20 per request today |
| `item_link_css_or_xpath` | hit list → item URLs | Declarative extractors (target) |
| `metadata_map` | citation_* meta tags → fields | Title, date, PDF URL, handle → `paper_id` |
| `formats_map` | `pdf`, `metadata` | PDF when `pdf_url` present |
| `http_states` | 403/404/timeout policies | IR/block pages; partial success OK |
| `user_agent` | required honest UA | Scraping-sensitive |
| `timing_hooks` | search HTML + per-item fetch | Usually slower than EPMC |

**Pilot sketch:**

```yaml
query_name: conicet_cambio_climatico
repository: conicet
query_string: cambio climatico
limit: 10
# start_date / end_date: omit until profile date_mode supports them
formats: [pdf, metadata]
timing: summary
fail_fast: false
corpus_name: conicet_cambio_climatico
```

---

### 2.3 Shodhganga (`shodhganga`)

| Profile control | Declarative intent | Notes (planned; see [south_asia.md](south_asia.md)) |
|-----------------|--------------------|-----------------------------------------------------|
| `capability` | `html_ir_search` or `rest_if_available` | Confirm public search/API before locking |
| `base_url` | `https://shodhganga.inflibnet.ac.in/` | National ETD reservoir |
| `material` | `thesis_etd` | PhD theses, not journal articles |
| `query_param` | site search field name | TBD from live HTML/API |
| `boolean` | declare `native` or `degraded` after probe | Do not claim EPMC-like Boolean until verified |
| `date_mode` | award/submission year if exposed | Map `start_date`/`end_date` or document unsupported |
| `limit` / pagination | bounded pilots only | Mandatory for size of corpus |
| `formats_map` | `pdf`, `metadata` (bitstream + DC-like fields) | Chapter PDFs possible later |
| `id_stem` | stable handle/accession → `paper_id` | Must fit `corpus` ID rules |
| `http_states` | 403/login walls / rate limits | Fail fast on forbidden; no credential stuffing |
| `timing_hooks` | search + large PDF downloads | Expect slower than EPMC |
| `access_notes` | MoU / membership caveats | Docs-only control: human checklist before live harvest |

**Pilot sketch (aspirational):**

```yaml
query_name: shodhganga_climate_theses
repository: shodhganga
query_string: climate change adaptation
limit: 5
# dates: only if profile declares support
formats: [pdf, metadata]
timing: summary
fail_fast: true
corpus_name: shodhganga_climate_theses
```

---

## 3. Side-by-side control matrix

| Control | EPMC | CONICET | Shodhganga |
|---------|------|---------|------------|
| `repository` id | `europe_pmc` | `conicet` | `shodhganga` |
| Boolean query | **Native** (strong) | **Degraded** (declare; strip wrappers today) | **TBD** — declare after probe |
| `start_date` / `end_date` | **Yes** (`FIRST_PDATE`) | **Not yet** (warn if set) | **TBD** |
| `limit` | Yes (API pageSize) | Yes (`rpp` / crawl cap) | Yes (mandatory) |
| Primary `formats` | `xml`, `pdf` | `pdf`, `metadata` | `pdf`, `metadata` |
| Capability class | REST JSON | HTML IR scrape | HTML IR / API TBD |
| Typical failure demos | 429, UA/403 | 403, HTML drift | access / 403 / large PDF |
| Maturity | In tree + pilots | In tree adapter | Planned target |

---

## 4. What users edit vs what they do not

| Edit (declarative) | Do not edit (for normal new pilots) |
|--------------------|-------------------------------------|
| Pilot YAML (`query_string`, dates, `limit`, `formats`, `timing`) | Core Python harvest engine |
| Site **profile** YAML (URLs, param names, boolean/date mode, xpath/css, http_states) | Ad-hoc one-off scripts per university |
| Env var *names* for tokens/UA overrides | Secrets committed in git |

---

## 5. Related

- Three targets: [target_examples.md](target_examples.md)  
- Strategy (engine, 403, timing): [strategy.md](strategy.md)  
- Tiny EPMC pilot (`limit: 2`): [`config/epmc_limit2_demo.yaml`](../../../config/epmc_limit2_demo.yaml)  
- Team demo write-up (Q&A + CLI): [epmc_declarative_demo.md](epmc_declarative_demo.md)  
- Larger EPMC pilot: [`config/ocean_heatwaves_2026.yaml`](../../../config/ocean_heatwaves_2026.yaml)
