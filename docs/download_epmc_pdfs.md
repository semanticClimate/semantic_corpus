# Europe PMC PDF download logic — process note for EPMC review

**Date of probe:** 2026-10-24 (system date / UTC probe timestamp below)  
**Software:** `semantic_corpus` (`EuropePMCRepository` in `semantic_corpus/repositories/europe_pmc.py`)  
**Audience:** Europe PMC / EBI web services team reviewing how we search and obtain PDFs  
**Raw probe artefacts:** `temp/epmc_pdf_probe_2026_10_24/` (local; not required to read this doc)

---

## 1. Purpose of this note

Europe PMC has asked partners not to scrape the website for bulk article PDFs, and the historical web render URL `https://europepmc.org/articles/{PMCID}?pdf=render` is no longer usable for automated clients (see §5).

This document explains **exactly** how `semantic_corpus` currently:

1. Submits a search query to the Europe PMC REST API  
2. Selects papers that claim PDF / OA / full text  
3. Attempts PDF download via an ordered list of sources  
4. Surfaces errors when a path fails  

We ran a **small live probe** (5 papers, PDF only) on 2026-10-24 and trapped the HTTP responses and library error messages below.

---

## 2. End-to-end process (our logic)

```text
YAML / CLI / Python
        │
        ▼
RepositoryFactory.get_repository("europe_pmc")

        │
        ▼
① search_papers(query, limit, …)
   GET https://www.ebi.ac.uk/europepmc/webservices/rest/search
   params: query, format=json, resultType=core, pageSize≤1000
        │
        ▼
② For each hit: normalize metadata (_paper_to_result)
   - pmcid, pmid, title, abstract, authors, doi, …
   - fullTextUrlList (publisher / PMC / Europe PMC links)
   - hasPDF, isOpenAccess flags from the API
        │
        ▼
③ download_paper(paper_id, output_dir, formats=["pdf"])
   Resolve PMCID if caller passed a PMID
        │
        ▼
④ _download_pdf(paper_id, paper, pmcid)  — try sources in order
   A. PMC Open Data on AWS S3   (if PMCID known)
   B. Europe PMC OA PDF FTP zip (if PMCID known)
   C. fullTextUrlList entries with documentStyle=pdf and
      availabilityCode in {OA, F}  (publisher or NCBI/EPMC links)
   D. https://europepmc.org/articles/{PMCID}?pdf=render   (legacy web)
        │
        ▼
⑤ _fetch_pdf(url)
   - GET url (timeout 60s)
   - if .zip → unzip and take first *.pdf
   - accept body only if it starts with %PDF
   - otherwise treat as failure (HTML/Cloudflare/JSON/empty)
        │
        ▼
⑥ If any PDF bytes obtained → write {paper_id}.pdf
   Else continue / if no files at all → raise RepositoryError
```

### 2.1 Search API (step ①)

- **Endpoint:** `GET https://www.ebi.ac.uk/europepmc/webservices/rest/search`  
- **Client:** Python `requests`  
- **Typical parameters:**

| Parameter | Value |
|-----------|--------|
| `query` | User/boolean query (see probe) |
| `format` | `json` |
| `resultType` | `core` (needed for `fullTextUrlList`, `hasPDF`, …) |
| `pageSize` | `min(limit, 1000)` |

Optional date window is AND-ed into `query` as `FIRST_PDATE:[start TO end]`.

We do **not** use SOAP, OAI-PMH, or browser automation for search.

### 2.2 PDF sources we attempt (step ④)

| Order | Source | URL pattern | Why we try it |
|-------|--------|-------------|---------------|
| A | PMC OA Open Data (AWS S3) | `https://pmc-oa-opendata.s3.amazonaws.com/{PMCID}.{v}/{PMCID}.{v}.pdf` after listing prefix `{PMCID}.` | Public OA dataset; not the europepmc.org HTML site |
| B | Europe PMC OA PDF FTP | `https://ftp.ebi.ac.uk/pub/databases/pmc/pdf/OA/PMCxxxxNNN/{PMCID}.zip` | Documented bulk OA PDF mirror ([downloads/openaccess](https://europepmc.org/downloads/openaccess)); monthly lag |
| C | API `fullTextUrlList` | Whatever Europe PMC returns with `documentStyle=pdf` and `availabilityCode` `OA` or `F` | Publisher or NCBI/EPMC free PDF links from the search record |
| D | Legacy web render | `https://europepmc.org/articles/{PMCID}?pdf=render` | Historical convenience URL; **fails for automated clients today** (see §5) |

**XML full text** (not the focus of this PDF note) still uses the REST full-text endpoint:

`GET https://www.ebi.ac.uk/europepmc/webservices/rest/PMC{id}/fullTextXML`

### 2.3 What we intentionally avoid

Per Europe PMC copyright / bulk-download guidance:

- We do **not** crawl or scrape article HTML pages for “Download PDF” buttons.  
- We do **not** use decommissioned backend URLs such as `/backend/ptpmcrender.fcgi`.  
- For large corpora we prefer API ID lists + OA FTP / Open Data mirrors over repeated website hits.

The remaining `?pdf=render` attempt (source D) is a **last resort** for single-article tooling compatibility; our probe shows it is currently blocked for scripts (§5).

---

## 3. Live probe design (5 PDFs)

| Field | Value |
|-------|--------|
| Probe UTC | `2026-10-24T14:05:05+00:00` |
| Query | `("marine heatwave" OR "ocean heatwave") AND OPEN_ACCESS:Y AND HAS_FT:Y AND HAS_PDF:Y` |
| Limit | **5** |
| Format requested | **pdf only** |
| Code path | `EuropePMCRepository.search_papers` → per-hit URL probes → `download_paper(..., formats=["pdf"])` |
| Output dir | `temp/epmc_pdf_probe_2026_10_24/downloads/` |

Papers returned (all `isOpenAccess=Y`, `hasPDF=Y`, with PMCID):

| # | PMCID | Title (short) |
|---|-------|----------------|
| 1 | PMC13655307 | Shift Towards Syndiniales Prevalence… Marine Heatwave |
| 2 | PMC13534446 | (OA marine heatwave hit) |
| 3 | PMC12980662 | (OA marine heatwave hit) |
| 4 | PMC13152010 | (OA marine heatwave hit) |
| 5 | PMC13120203 | (OA marine heatwave hit) |

---

## 4. Probe results summary

| Metric | Result |
|--------|--------|
| Search | Success — 5 hits from REST `/search` |
| `download_paper` with current fallbacks (A→D) | **5 / 5 PDF success** |
| Successful source in practice | **A — PMC OA S3** for all five |
| `?pdf=render` (source D) alone | **0 / 5** — see trapped errors below |
| Europe PMC OA FTP zip (source B) | Mix of **404 Not Found** (newer IDs) and non-PDF / empty responses |
| NCBI `…/pmc/articles/…/pdf/?tool=EBI` from `fullTextUrlList` | HTTP 200 but **not** `%PDF` (HTML / interstitial) for probed cases |

So: **search works; website PDF render fails for automation; OA Open Data S3 still supplies PDFs for these OA PMCIDs.**

---

## 5. Trapped error messages (for EPMC)

### 5.1 Website PDF render — consistent failure

For every probed PMCID, the URL advertised in `fullTextUrlList` and used as our last resort:

```text
https://europepmc.org/articles/{PMCID}?pdf=render
```

returned:

| Field | Observed value |
|-------|----------------|
| HTTP status | **403 Forbidden** |
| `Content-Type` | `text/html; charset=UTF-8` |
| HTML `<title>` | **Just a moment...** |
| Body start | Cloudflare challenge HTML (`<!DOCTYPE html>…`) |
| PDF magic `%PDF` | **false** |

**Example trapped HTTP error string (requests):**

```text
403 Client Error: Forbidden for url: https://europepmc.org/articles/PMC13655307?pdf=render
```

(Same pattern for PMC13534446, PMC12980662, PMC13152010, PMC13120203.)

This matches automated clients being stopped at the CDN/WAF rather than receiving a PDF stream. Browser users may still open PDFs on the site; our tooling does not solve Cloudflare interactively.

### 5.2 Library error when only `?pdf=render` is used

If we disable S3/FTP/publisher fallbacks and only call `_fetch_pdf` on `?pdf=render`, `download_paper` raises:

```text
RepositoryError: No files downloaded for PMC13655307
RepositoryError: No files downloaded for PMC13534446
RepositoryError: No files downloaded for PMC12980662
RepositoryError: No files downloaded for PMC13152010
RepositoryError: No files downloaded for PMC13120203
```

That is the **application-level** error our users see when no alternative PDF source succeeds. Underlying cause for the render URL is the **403 + Cloudflare HTML** above (not a Europe PMC JSON error body).

### 5.3 Europe PMC OA FTP zip — example failures

Newer PMCIDs were often missing from the monthly FTP tree at probe time:

```text
404 Client Error: Not Found for url:
https://ftp.ebi.ac.uk/pub/databases/pmc/pdf/OA/PMCxxxx1366/PMC13655307.zip
```

HTML title: `404 Not Found`.  
(Expected if the FTP OA PDF set lags the newest articles.)

### 5.4 What still succeeds (context for EPMC)

PMC Open Data S3 for the same IDs returned **HTTP 200** with `%PDF-1.x` bodies, e.g.:

```text
https://pmc-oa-opendata.s3.amazonaws.com/PMC13655307.1/PMC13655307.1.pdf
→ 200, Content-Type: binary/octet-stream, starts with %PDF-1.7
```

Our current default path therefore completes PDF download **without** relying on `europepmc.org/?pdf=render`.

---

## 6. Alignment with Europe PMC guidance (our reading)

From public Europe PMC developer / copyright pages and the developer forum discussion on PDF render / `ptpmcrender.fcgi`:

| Guidance | Our response |
|----------|----------------|
| Do not systematically scrape the website for articles | We use REST search + OA mirrors; `?pdf=render` is last resort only |
| Prefer bulk OA downloads ([FTP PDF OA](https://europepmc.org/ftp/pdf/), [open access downloads](https://europepmc.org/downloads/openaccess)) | Implemented as source B; accept monthly lag / gaps |
| REST for metadata / IDs / XML full text | Search + `fullTextXML` used as primary machine APIs |
| Legacy `ptpmcrender.fcgi` decommissioned | We never call `fcgi`; only `?pdf=render` remains as fallback and currently 403s for scripts |

We welcome confirmation from EPMC on the **preferred programmatic PDF path** for query-sized sets (tens to hundreds of OA PMCIDs), e.g.:

1. Search API → PMCID list → PMC OA Open Data / FTP only, or  
2. An official non-Cloudflare HTTPS PDF URL for OA articles, or  
3. Explicit guidance to stop using `?pdf=render` in clients entirely.

---

## 7. Implementation reference (code map)

| Step | Symbol | File |
|------|--------|------|
| Repository registration | `RepositoryFactory` → `"europe_pmc"` | `semantic_corpus/core/repository_factory.py` |
| Search / metadata / download | `EuropePMCRepository` | `semantic_corpus/repositories/europe_pmc.py` |
| PDF candidate order | `_download_pdf` | same |
| HTTP fetch + `%PDF` check | `_fetch_pdf` | same |
| S3 listing | `_s3_pdf_url` | same |
| FTP zip URL | `_ftp_pdf_url` | same |
| Filter API PDF links | `_full_text_pdf_urls` | same |
| Errors | `RepositoryError` | `semantic_corpus/core/exceptions.py` |

Constants:

```text
REST base:     https://www.ebi.ac.uk/europepmc/webservices/rest
PMC OA S3:     https://pmc-oa-opendata.s3.amazonaws.com
OA PDF FTP:    https://ftp.ebi.ac.uk/pub/databases/pmc/pdf/OA
Web render:    https://europepmc.org/articles/{PMCID}?pdf=render
```

---

## 8. How to reproduce the probe

```bash
cd /path/to/semantic_corpus
source venv/bin/activate

python - <<'PY'
from pathlib import Path
from semantic_corpus.repositories.europe_pmc import EuropePMCRepository

repo = EuropePMCRepository()
q = '("marine heatwave" OR "ocean heatwave") AND OPEN_ACCESS:Y AND HAS_FT:Y AND HAS_PDF:Y'
hits = repo.search_papers(query=q, limit=5)
out = Path("temp/epmc_pdf_probe_repro")
out.mkdir(parents=True, exist_ok=True)

for h in hits:
    pid = h["pmcid"] or h["pmid"]
    try:
        print(pid, repo.download_paper(pid, out, formats=["pdf"]))
    except Exception as e:
        print(pid, type(e).__name__, e)
PY
```

To **trap the website failure alone**, request only:

`GET https://europepmc.org/articles/PMC13655307?pdf=render`  

and inspect status **403** + HTML title **Just a moment...**.

---

## 9. Questions for Europe PMC

1. Is **403 + Cloudflare** on `?pdf=render` the intended long-term behaviour for non-browser clients?  
2. Should machine clients **remove** `?pdf=render` entirely and use only FTP / Open Data / publisher links from `fullTextUrlList`?  
3. For articles in OA XML but **not yet** on the monthly PDF FTP, is **PMC OA S3** (`pmc-oa-opendata`) considered an approved source from EPMC’s perspective?  
4. Is there a supported **per-PMCID PDF URL** on `*.ebi.ac.uk` / FTP that does not pass through Cloudflare?

---

## 10. Contact / project context

- Project: **semanticClimate / semantic_corpus** — open tools for building small, citable climate literature corpora (search → download → review → encyclopedia / local RAG).  
- Europe PMC is our primary biomedical/open literature search backend for many demos.  
- We are happy to adjust client logic to match EPMC’s recommended PDF pipeline.

---

*This document describes observed behaviour of public HTTP endpoints and our open-source client as of the probe date. It is not a complaint ticket; it is a transparent description for joint review of download logic.*
