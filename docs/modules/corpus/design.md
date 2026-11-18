# Design specification — `corpus` (standalone core)

**Status:** draft v0.3  
**Module:** [`corpus`](overview.md) · package face: `semantic_corpus.corpus`  
**Audience:** personal / project corpora — **not** production institutional-repository (IR) operations  

**Prompts that drove this specification (JOSS audit trail):**

1. [discussions/prompt_2026-11-18_corpus_design.md](../../../discussions/prompt_2026-11-18_corpus_design.md)  
2. [discussions/prompt_2026-11-18_corpus_design_cont.md](../../../discussions/prompt_2026-11-18_corpus_design_cont.md)  
3. [discussions/prompt_2026-11-18_zotero_vs_corpus.md](../../../discussions/prompt_2026-11-18_zotero_vs_corpus.md) (+ follow-ons on offline, full text, interop)  
4. [discussions/prompt_2026-11-18_corpus_functionality_users.md](../../../discussions/prompt_2026-11-18_corpus_functionality_users.md)  

**Related:** [joss_presentation.md](joss_presentation.md) · [../../joss_series_strategy.md](../../joss_series_strategy.md) · [../README.md](../README.md)

---

## 0. Positioning

| `corpus` is | `corpus` is not |
|-------------|-----------------|
| A **lightweight filestore-as-database** for a researcher’s or project’s literature | A production IR (DSpace, Invenio, Fedora, …) or library systems stack |
| BagIt-first preservation of documents, diagrams, tables-as-files | A host for research *databases* / data cubes |
| Declarative ingest + semantic overlay + incremental `doit` | A black-box agent that harvests without human limits (v1) |
| CRUD-shaped curation for **personal** corpora | Multi-tenant IR policy, embargo workflows, or institutional deposit APIs |
| A substrate sibling modules and tools can feed | A replacement for Zotero’s bibliographic UX |

Sibling module **`repositories`** owns gathering/adapters for many scholarly sources; `corpus` supplies **ingest hooks**, BagIt/layout contracts, cleaning/semanticisation, and an EPMC-oriented **example** others can copy. **Zotero** is a bibliographic discovery neighbour that can **interoperate** as an ingest source (§5.4).

---

## 1. Who uses it, and for what

`corpus` is for people who need a **citable, incremental, on-disk project corpus**—not only a reading list.

| Persona | Typical goal | How they use `corpus` |
|---------|--------------|------------------------|
| **Domain researcher** (e.g. climate, health) | Build a bounded literature set for a paper or review | Declarative YAML query or closed file list → ingest with limits → BagIt → review table to drop noise |
| **Systematic / narrative reviewer** | Grow a corpus over months without re-downloading | Stop mid-run; **rerun** skips satisfied entries; add next *N* hits or next IPCC volume |
| **Methods / RSE** | Reproducible intake for a lab or JOSS demo | Commit configs + cleaner packs; CI tests on real fixtures; share the bag as the artefact |
| **Non-coder curator** | Adjust extraction without editing Python | Edit XPath/regex/YAML cleaner packs; re-run semanticisation only |
| **Sibling-module author** (`repositories`, `phrases_kg`, …) | Consume a stable layout | Call ingest hooks or read BagIt + semantic HTML / review table by contract |
| **Zotero-centred reader** | Keep discovery in Zotero, analysis in a project tree | Capture in Zotero → export/API/storage → `corpus` ingest → semantic HTML for KG/chat/export |

**Anti-personas:** IR managers needing deposit workflows, multi-tenant access control, or production harvest of an entire national repository—that is out of scope.

---

## 2. Functionality catalogue

Capabilities below are the **product surface** of `corpus`. Status tags: **now** = largely present in tree; **target** = specified for the JOSS core claim.

### 2.1 Corpus lifecycle

| Function | What it does | How people use it |
|----------|--------------|-------------------|
| **Create / open corpus** | Initialise or reopen a workdir (BagIt or flat→BagIt path) | `create` once per project; reopen for every later ingest/review |
| **Configure declaratively** | YAML/JSON describes sources, limits, formats, cleaner packs | Edit config locally; share config in git without changing core code |
| **Validate layout** | Check BagIt / path contracts / manifests | Before demos, CI, or hand-off to another module |

### 2.2 Ingest (Create + Rerun)

| Function | What it does | How people use it |
|----------|--------------|-------------------|
| **Schema-light intake** | Accept material without a fixed upstream schema; guess type where needed | Drop PDFs/DOCX, pygetpapers dirs, query JSON, Zotero export—human confirms limits |
| **Closed-set ingest** | Enumerate a finite collection (e.g. IPCC WGs/SRs, a thesis list) | Run until complete or stop; resume later without redoing done items |
| **Sampled query ingest** | Pull up to *N* hits from a service (EPMC example in-core) | Pilot with small *N*; grow with reruns of “next chunk” |
| **Stop / limit** | Human interrupt or configured caps end a run safely | Ctrl-C or `limit:` in YAML; nothing half-claimed should look “done” |
| **Skip-satisfied rerun** | `doit`-like: detect successfully ingested entries and skip | Re-run the same config after a crash or overnight stop |
| **Software/rules rerun** | Re-derive overlays when cleaners or code change | Bump cleaner pack version; reprocess without re-fetching every PDF |
| **Optional user schema** | After BagIt, optionally enforce a user-declared shape | Labs that want extra path/metadata conventions on top of BagIt |

### 2.3 Cleaning and semanticisation

| Function | What it does | How people use it |
|----------|--------------|-------------------|
| **Legacy → HTML convert** | PDF, DOCX/OOXML/Word-HTML → HTML | Automatic downstream task after raw ingest |
| **CMS / web HTML clean** | Gatsby, WordPress (etc.) HTML → structured HTML | Ingest saved pages or site exports; apply declarative cleaners |
| **Mint structure + IDs** | Sections, paragraphs; figures+captions; tables+captions | Downstream phrase/KG/chat read stable chunk IDs |
| **Declarative cleaner library** | Packs for Docling/PDF, OOXML/DOCX, Gatsby, WordPress, … | Non-coders swap packs; authors contribute packs without forking ingest |

### 2.4 Read, search, curate (CRUD-shaped)

| Function | What it does | How people use it |
|----------|--------------|-------------------|
| **Read by ID** | Resolve entry to raw file and/or semantic HTML | Scripts and sibling modules; “open this PMCID” |
| **List / browse** | Enumerate corpus membership | CLI or HTML table |
| **Regex search** | Search filenames and/or contents | Find stragglers, junk PDFs, caption text before delete |
| **Delete / tombstone** | Remove or mark gone; refresh index/UI | Manual curation in the review table |
| **Update** | Rare in-place change | Prefer delete+reingest or overlay rerun; document if used |

### 2.5 Review UI

| Function | What it does | How people use it |
|----------|--------------|-------------------|
| **HTML review table** | Browse, Read, Delete, regex filter | Weekly QA pass; internship curation; JOSS demo of transparency |
| **Ingest QA columns** | Review-table vocabulary as quality gate | Include/exclude decisions without being the science product |

### 2.6 Interop hooks

| Function | What it does | How people use it |
|----------|--------------|-------------------|
| **Ingest hooks for `repositories`** | Stable API/contracts adapters call | Larisa (etc.) add SciELO/Redalyc without new BagIt dialects |
| **EPMC worked example** | Reference adapter + docs to clone | Copy pattern for a new repository |
| **Zotero interop** | Optional ingest from library/export/Local API/storage | Discovery in Zotero → project corpus in BagIt (§5.4) |
| **Export bridge** | Thin hand-off toward chatbot/RAG (not chat UX) | Stable export contract for sibling papers |

### 2.7 Incremental processing engine

| Function | What it does | How people use it |
|----------|--------------|-------------------|
| **`doit`-like task graph** | Dependencies: fetch → store → clean → semanticise → index/UI | One command resumes the whole chain; satisfied steps skip |
| **Optional secondary index** | Accelerate lookup when the bag grows | Enable only when filename walks become painful |

---

## 3. Usage scenarios (end-to-end)

### A. Pilot query corpus (days)

1. Create corpus workdir.  
2. YAML: EPMC query, `limit: 20`, formats PDF/XML.  
3. Ingest → BagIt; optional clean/semanticise.  
4. Open HTML review table; delete off-topic hits.  
5. Commit config + bag (or bag pointer) for the project.

### B. Grow the same corpus over a project (months)

1. Raise limit or set “next *N*”.  
2. Rerun: satisfied entries skip; only new hits fetch.  
3. Re-run cleaners after improving a PDF pack—overlays refresh, originals kept.  
4. Hand BagIt + semantic HTML to `phrases_kg` or export bridge.

### C. Closed report set (IPCC-style)

1. Declarative list of volumes/URLs/files (finite).  
2. Ingest until complete or stop; resume later.  
3. Semanticise chapters to section/paragraph/figure/table IDs for quoting and indexing.

### D. Local theses / grey PDF pile

1. Point ingest at a folder of PDFs/DOCX (schema-free).  
2. Guess types; apply Docling/DOCX cleaners.  
3. Review table regex on filenames; delete scans that failed conversion.

### E. Zotero → corpus

1. Build bibliographic set in Zotero (local, offline-capable).  
2. Export or Local API / copy attachments into corpus ingest.  
3. BagIt + semanticise for analysis; keep Zotero for reading/citing.

### F. Sibling adapter author

1. Use corpus ingest hooks + EPMC example.  
2. Implement Redalyc (etc.) in `repositories`.  
3. Same review table and BagIt contracts—no parallel vocabulary.

---

## 4. System model

```
                    ┌─────────────────────────────┐
  human / limits ──►│ declarative ingest configs  │
                    └──────────────┬──────────────┘
                                   ▼
┌──────────────┐   raw bytes    ┌──────────────────┐   optional   ┌─────────────┐
│ sources      │───────────────►│ BagIt filestore  │◄────────────►│ 2° index    │
│ (files,      │                │ (source of truth)│   lookup     │ (NoSQL-ish) │
│  query hits, │                └────────┬─────────┘              └─────────────┘
│  Zotero, …)  │                         │ doit tasks
└──────────────┘                         ▼
                              ┌──────────────────────┐
                              │ cleaners +           │
                              │ semanticisation      │
                              │ → structured HTML    │
                              │   (+ IDs, chunks)    │
                              └──────────┬───────────┘
                                         ▼
                              ┌──────────────────────┐
                              │ HTML review table UI │
                              │ Browse/Read/Delete/  │
                              │ regex search         │
                              └──────────────────────┘
```

| Layer | Responsibility |
|-------|----------------|
| **BagIt filestore** | Authoritative store of non-semantic (or pre-semantic) literature artefacts |
| **Secondary index** | Optional; accelerates search when collections grow; never replaces the bag |
| **Semantic overlay** | Derived sections/paragraphs, figures+captions, tables+captions (HTML builtins preferred) |
| **Declarative control** | YAML/JSON (+ XPath/regex packs) drive ingest and cleaners; core code stays material-agnostic |
| **Task engine** | `doit`-like dependency graph for incremental Create / Rerun / skip-satisfied |

---

## 5. Design principles

1. Filestore (BagIt) is the database; indexes are accelerators.  
2. CRUD-shaped API; Update rare; Rerun for software/rules and incremental harvest.  
3. Schema-free intake; guess + declare; optional user schema after BagIt.  
4. Humans in the loop for intake control (v1).  
5. Declarative ingest + semanticisation; code independent of which literature is ingested.  
6. Finite collections vs sampled queries — both first-class; both stoppable and resumable.  
7. Interoperate with bibliographic tools (Zotero); do not re-implement them.  
8. Personal/project scale—not IR production operations.

---

## 6. Non-functional constraints

1. Personal-corpus scale first; optional index only when needed.  
2. Prefer declarative external assets (YAML, cleaner packs, HTML/JS outside core).  
3. Real fixtures in tests; **no mocks** for claimed ingest behaviour.  
4. Incremental, idempotent tasks: safe interrupt and resume.  
5. Entries mostly immutable; software-driven Rerun re-derives overlays without silently rewriting provenance of originals unless explicitly configured.

---

## 7. Out of scope (this module)

- Production IR deposit, access-control, and preservation *services* for institutions  
- Full Global South / multi-repo adapter portfolio (→ `repositories`)  
- Phrase/KG science (→ `phrases_kg`)  
- Encyclopedia content systems; chatbot UX  
- Autonomous multi-step agent ingest (future option only)  
- Replacing Zotero/JabRef as the primary bibliographic UI  

---

## 8. Overlapping and complementary tools

`corpus` **composes and contracts** around tools; it does not try to replace institutional stacks or become “yet another downloader.”

### 8.1 Complementary (use / wrap / declare)

| Tool / approach | Relation to `corpus` |
|-----------------|----------------------|
| **BagIt** | Native packaging target for the filestore |
| **doit** (or equivalent) | Incremental task graph: skip-satisfied, resume, trigger clean/semanticise |
| **pygetpapers** | Upstream harvest layout corpus already ingests; example pathway into BagIt |
| **Europe PMC / OpenAlex APIs** | Query sources; thin example in corpus, richer adapters in `repositories` |
| **Docling**, **Marker**, **MinerU**, **Nougat** | PDF/office → structured HTML/Markdown/JSON candidates for the **cleaner library** |
| **GROBID** / **CERMINE** | Scholarly PDF → TEI/JATS; complementary when metadata/refs matter more than HTML chunks |
| **pandoc** / **mammoth** / OOXML tooling | DOCX / Word-HTML conversion paths |
| **HTML/CSS/XPath + regex packs** | Declarative cleaners for Gatsby/WordPress and post-conversion HTML |
| **Existing `corpus_review` HTML viewer** | Basis for Browse/Read/Delete/regex UI |
| **Zotero** | Bibliographic search/library UX; optional ingest source (§8.4) |

### 8.2 Overlapping (position carefully in JOSS State of the field)

| Tool / approach | Overlap | Differentiation for personal `corpus` |
|-----------------|---------|----------------------------------------|
| **Zotero / JabRef / Mendeley** | Personal libraries, PDF attach, local full-text index | See **§8.4** — interoperate; Zotero is not the substrate |
| **pygetpapers alone** | Search + download | We own post-download filestore, cleaning, semantic IDs, resume/skip, review CRUD UI |
| **IR platforms (DSpace, Invenio, EPrints, Samvera)** | Long-term lit storage | Explicitly **out of scope** |
| **Semantic Scholar / CORE bulk** | Large-scale lit access | We target **bounded** personal/project subsets with human limits |
| **Ad-hoc PDF folders + scripts** | Common practice | We standardise IDs, BagIt, declarative cleaners, resumable tasks |
| **Generic ETL / Airflow** | Pipelines | Lightweight researcher-local `doit`-scale |

### 8.3 Build-vs-contribute stance (for JOSS)

The scholarly contribution is the **personal-corpus substrate**: BagIt-as-DB + schema-light declarative ingest + skip-satisfied incremental processing + semantic HTML overlay + human review table—with hooks so `repositories` and others plug in without forking a second layout vocabulary—and **interop** with bibliographic tools such as Zotero rather than competing with them.

### 8.4 Zotero in detail

| Question | Answer for JOSS / design |
|----------|--------------------------|
| **Where is the overlap?** | Both target **personal** scholarly collections: store PDFs/docs, metadata, browse/search, human curation, offline-capable workflow. |
| **Can Zotero run locally?** | **Yes.** Desktop + local SQLite; optional sync; Local API on localhost. |
| **Offline / no server?** | **Yes** for personal use; zotero.org sync is optional. |
| **Full text locally?** | Metadata always local; **full documents** local when attached/linked; optional full-text index. |
| **Does Zotero semantify?** | **Not in our sense** (no BagIt + structured HTML chunk IDs + declarative cleaner packs as core). |
| **Core engine for `corpus`?** | **No.** |
| **Ingest option?** | **Yes — as a source** (storage, export, Local API) → BagIt + clean/semanticise. |
| **Role** | **Bibliographic search & library UX** that **interoperates** with `corpus` (preservation + semantic filestore). |
| **Interop patterns** | Zotero → corpus ingest; optional bibliographic push-back; join on DOI/PMCID/…. |

**Unique to `corpus` (vs Zotero):** BagIt-as-DB; declarative skip-satisfied ingest; semantic HTML overlay + cleaner library; sibling-module contracts; scriptable project corpora—not reference-manager parity.

---

## 9. Implementation sketch (non-normative)

| Concern | Likely home (today → target) |
|---------|------------------------------|
| Corpus open/create | `core/` / `CorpusManager` → `semantic_corpus.corpus` |
| Ingest hooks | `ingestion/` |
| BagIt | `storage/` |
| doit / resume | `pipeline/` |
| Review HTML table | `corpus_review/` |
| EPMC example | thin face in corpus; shared adapter under `repositories/` |
| Cleaner packs | new declarative library under corpus (path TBD) |
| Zotero ingest recipe | optional docs/extra under corpus |

---

## 10. Open items

- Tombstone vs hard-delete semantics  
- Concrete secondary-index choice (if any)  
- Formal user-schema language beside BagIt  
- Cleaner pack schema versioning and Rerun invalidation keys  
- Default install vs extras for EPMC example / Zotero recipe / heavy cleaners  

---

## 11. Prompt discipline (JOSS)

Archive human prompts under `discussions/` and link them here so reviewers can see that design and code track **author strategy**, including series ownership and community transcripts ([joss_series_strategy.md](../../joss_series_strategy.md) §4).
