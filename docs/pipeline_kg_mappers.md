# KG mappers: terms × text packets

**Date:** 2026-11-05  
**Status:** design (implementation follows)  
**Parent:** [pipeline.md](pipeline.md) · [pipeline_examples.md](pipeline_examples.md) · [pipeline_next_encyclopedia_kg.md](pipeline_next_encyclopedia_kg.md) · tutorial [tutorials/kg_from_query.md](tutorials/kg_from_query.md)

## 1. Problem

We build knowledge graphs over corpora in more than one place:

| Setting | Terms | Packets (under containers) |
|---------|-------|----------------------------|
| Query → corpus KG (this repo) | phrases / terms | papers as containers; today often one body packet |
| Glossary → figures (elsewhere) | glossary terms | figure / table captions |

**Shared idea:** **match / annotate** terms against structurally **indexed packets** (and optionally build homogeneous term–term or packet–packet edges), then assemble **one graph** (possibly with disjoint subgraphs) and display filtered views.

The current `kg` step hard-codes document incidence (`clusters` / paper↔term). We generalise so several **mappers** can contribute typed edges to that single graph.

## 1.1 Canonical pipeline

End-to-end flow of the components above:

```text
1. Search + collect documents     [doit: search → paper:{id} → collect]
      flat files under --workdir: {id}.json|.xml|.pdf|.pdf.xml
      (few large docs e.g. IPCC, or many papers e.g. EPMC)
        │
2. Corpus (gate + indexes)
      ensure corpus (flat or legacy BAGIT); ensure text components have
      structural packet indexes (if not already indexed in source)
        │
3. Terms
      traverse indexed packet texts → extract if required  (extracted)
      and/or load external ontology/glossary (authority)
        │
4. Map (incidence + communities)   [doit: clusters]
      match terms ↔ packet texts ⇒ bipartite BKG + communities
      optional --kg → **KG₁** (unannotated display graph; cheap)
        │
5. Curate (graph FPs)              [doit: clean]
      remove false-positive terms/packets using BKG / islands
      *before* spending annotate effort
        │
6. Annotate terms   [doit: encyclopedia]
      attach authority payloads to *retained* terms
      (Wikipedia/Wikidata page, gloss, image, Q-id, …)
      optional --kg → **KG₂** (annotated display; may add Wikidata links)
```

Packet text cascade: `{id}.xml` → `{id}.pdf.xml` → abstract in `{id}.json`.

| Design step | Inputs | Outputs |
|-------------|--------|---------|
| **Collect documents** | live search, local paths, … | flat document files / containers in the corpus |
| **Corpus** (+ indexes) | containers (+ source structure) | corpus root **and** **packets** with stable addresses |
| Terms | packets and/or authority lexicons | term set (`extracted` and/or `authority`) |
| **Map** (`clusters`) | terms × packet texts | bipartite BKG + communities; optional **KG₁** via `--kg` |
| **Curate** (`clean`) | clusters-stage graph | fewer FP terms/packets |
| **Annotate terms** | retained term set | payloads; optional **KG₂** via `--kg` |

**Two knowledge graphs** (display artifacts — **not** doit steps):

| Graph | When | Contents |
|-------|------|----------|
| **KG₁** | `clusters --kg` | term↔packet incidence only (no wiki annotation) |
| **KG₂** | `encyclopedia --kg` | KG₁ plus Wikipedia payloads; may include external Wikidata links |

`--kg` / `--no-kg` is a flag on those steps (little extra compute). `pipeline kg` remains a rebuild helper.

**Formal doit names (today):**

| Design | Doit today | Notes |
|--------|------------|--------|
| Collect documents | `collect` | `--query` remotes or `--source` static |
| Corpus (+ packet indexes) | **`corpus`** | bag + `packets/manifest.json` |
| Terms (extracted) | `phrases` | traverses indexed packet texts |
| Map | **`clusters`** | optional `--kg` → KG₁ |
| Curate | **`clean`** | after `clusters`; before encyclopedia |
| Annotate terms | **`encyclopedia`** | after `clean`; optional `--kg` → KG₂ |

Full spine: `collect → corpus → phrases → clusters → clean → encyclopedia`.

There is **no separate doit `index` or `kg` step** — indexes live under `corpus`; display KGs are flags.

## 2. Core vocabulary

**Naming:** we use **packet**, not “chunk”. In current AI tooling, “chunk” usually means LLM/RAG splitting; that is *not* what we do. Packets are structural index units from the source (or containment/sequence fallbacks).

```text
Collect documents (containers)   [doit: collect]
                                   options: --query remotes | --source static
   → Corpus (+ packet indexes)            [doit: corpus → packets/]
   → Terms (traverse texts)               [doit: phrases ± glossary]
   → Map (BKG + communities)              [doit: clusters]  [--kg → KG₁ plain]
   → Curate (drop graph FPs)              [doit: clean]
   → Annotate retained terms              [doit: encyclopedia]  [--kg → KG₂ annotated]
```

### Term

A lexical object used to **match / annotate** packets (and optionally to hang homogeneous ontology links).

- Stable id: `term:<normalized_phrase>`
- Fields: `phrase`, `display`, optional `n_papers` / score, optional synonyms after collapse, optional `term_origin`
- **Term annotations / payloads** (gloss, image, wiki blurb, Q-id, …): produced chiefly by **Annotate terms** (`encyclopedia`); start as **payload on the term** for display; may later be promoted to their own **packets** if they become index units
- Viewer: blue (`group=Term`, `kind=term`)

#### Term / annotation lexicon origins

The vocabulary that annotates packets may be:

| Origin | Meaning | Examples |
|--------|---------|---------|
| **Authority** (`authority`) | External / given lexicon or ontology | Wikidata entities & aliases; IPCC glossary; domain thesauri |
| **Extracted** (`extracted`) | Terms induced from packet text | Keyphrases from EPMC body packets (`phrases/`) |

**Both may be used at once** in the same graph (and even in the same mapper run): e.g. extracted phrases for incidence plus authority glossary/Wikidata for stronger labels, ontology links, and synonym consolidation. Stamp `term_origin` (`authority` \| `extracted`) — or per-edge evidence — so views can filter by origin.

*(Avoid “curated” for lexicon origin — that clashes with pipeline step **Curate** (island removal). Avoid “supervised / unsupervised” — those suggest ML training regimes.)*

### Packet

A **structurally delimited** text unit that can later be **matched / annotated**. Packets exist because of **indexing**, not because a query or LLM splitter hit them.

| `packet_type` | Example id | Typical text |
|---------------|------------|--------------|
| `frontmatter` | `fm:<paper_id>:…` | title block, abstract, keywords, … (may be empty) |
| `body` | `body:<paper_id>:…` / `para:…` | body paragraphs / sections (may be empty) |
| `backmatter` | `bm:<paper_id>:…` | refs, supplements, … (may be empty) |
| `caption` | `caption:<figure_id>` | figure / table caption |
| `abstract` | `abstract:<paper_id>` | abstract as its own packet when indexed separately |

Today’s EPMC path often uses a single degenerate **body** packet standing for “the whole paper text”; that is a packaging shortcut, not a claim that the paper *is* a packet.

- Fields: `label`, `title` / tooltip, optional `text`, stable **index address** (see §2.1), `parent_id` → container
- Viewer: orange often shows the **paper container** (legacy `group=Paper`); caption packets may use `group=Caption`

### Container

A structural parent. **A paper is always a container.** It contains **frontmatter**, **body**, and **backmatter** regions; any of those may be empty, and each region may hold zero or more packets (paragraphs, captions, …). Chapters, figures, and tables may also be containers.

Containers are for provenance and hierarchy. Matching targets are **packets** (unless a UI collapses a container to its sole packet for display).

### Graph shapes: bipartite vs homogeneous

Two families of **edges** share one node inventory (and live in **one graph**).

| Shape | Nodes involved | Edges | Examples |
|-------|----------------|-------|----------|
| **Bipartite (heterogeneous)** | terms and packets | term↔packet only | EPMC incidence BKG; glossary↔caption |
| **Homogeneous (monotypical)** | one node kind | same-kind ↔ same-kind | Wikidata / ontology term–term; packet–packet `isSimilarTo` |

**Homogeneous edges** come from:

1. **External structure** — ontologies / thesauri / SKOS / Wikidata neighbours already asserted outside the corpus.
2. **Internal similarity** — compare payloads on two nodes of the same kind, e.g. `text1.isSimilarTo(text2)` for packets, or label/gloss similarity for terms.

**Storage:** one assembled graph with typed edges (`edge_class`, `mapper_id`). Subgraphs may be **disjoint**. Viewers filter (e.g. incidence-only bipartite HTML); they do not imply separate on-disk graphs.

### Edge classes

| Class | Shape | Meaning | Typical producer |
|-------|-------|---------|------------------|
| term↔packet | bipartite | match / annotate term in packet text | `doc_phrases`, `caption_glossary`, wikipedia-as-annotator, … |
| term↔term | homogeneous | synonym, hierarchy, ontology link | wikipedia/Wikidata ontology; other ontology mappers; similarity |
| packet↔packet | homogeneous | `text_i` similar to `text_j`, discourse, citation | similarity mapper; structural links |

### Mapper

Runs **after** packets (and terms) exist. **Every** edge-producing process is a **mapper** (including Wikipedia/Wikidata). A mapper may emit bipartite and/or homogeneous edges; assemble records `edge_class` / `mapper_id`.

```text
Mapper.run(workdir, *, terms?, packets?, filters?) → {nodes, edges, meta}
```

Mappers do **not** invent packet boundaries or own HTML.

**Wikipedia / Wikidata** appears in two places:

1. **`encyclopedia` (Annotate terms)** — resolve selected terms to wiki/Wikidata pages and write **payloads** on terms (`entries.json`). Primary sense of “annotating terms.”
2. **`wikipedia` mapper (Map)** — may use those payloads plus live/ontology structure:

| Role | What it contributes |
|------|---------------------|
| (a) Ontology | homogeneous term↔term (and entity) structure from Wikidata |
| (b) Lexicon | canonical labels / aliases as term vocabulary |
| (c) Packet annotator | match terms/entities in packet text; optional synonym collapse for incidence views |

### 2.1 Indexing (before mapping; never search)

**Indexing** builds the inventory of packets and their stable addresses from document structure. It is independent of terms, queries, mappers, and LLM ingestion.

**Priority (first match wins):**

1. **Authoritative source numbering** — ideally already present before ingestion (e.g. numbered paragraphs in the publisher/XML/IPCC source). Prefer these ids unchanged.
2. **Containment** — if the source has hierarchy (article → section → paragraph; report → chapter → figure → caption), index by that tree; packet ids reflect the path.
3. **Sequence** — otherwise assign sequential addresses within each container (paragraph 1…n in document order).

**Hard rule:** indexing **must not** depend on retrieval or matching (no “packets = passages that matched the query”, no embedding-defined spans as the primary index). Mappers only **match / annotate** already indexed packets.

**Ingestion:** prefer to ingest pre-indexed structure; if the bag only has raw text/XML, run a structural indexer at ingest (containment → sequence). Packet **bytes** may stay in the original container file (addressed by offset/xpath/section id) or be materialized as unique packet files; either way a **manifest** (e.g. under `data/indices/` or `packets/`) lists ids and addresses before any mapper runs.

| Source | Ideal index | Fallback |
|--------|-------------|----------|
| Europe PMC JATS/XML | section/paragraph ids from XML | whole-document packet (today) → later sequential paras |
| IPCC | numbered paragraphs / figure captions in source | chapter containment + sequence |

**EPMC content streams** (independent; a 500 disables **only** that stream):

| Stream | Role | On 500 |
|--------|------|--------|
| **JSON** | search + `*_metadata.json` (title/abstract) | Job cannot collect — stop |
| **XML** | publisher `fullTextXML` | Discontinue XML; keep JSON/PDF |
| **PDF** | OA PDF mirrors | Discontinue PDF; keep JSON/XML |

If **XML is blocked** but PDF is available → **Docling PDF → XML** (then phrase/packet text can use that XML).

**Packet text payload cascade** (when resolving bytes for a body packet / phrases; first non-empty wins):

1. **XML** — valid publisher/JATS or Docling-made XML (optional section selector)
2. **PDF** — Docling HTML sidecar / convert when needed
3. **JSON abstract** — from `*_metadata.json`

## 3. Mapper catalogue

| Id | Terms from | Packets from | Role |
|----|------------|--------------|------|
| `doc_phrases` | phrases / BKG membership | body (or degenerate whole-text) packets under paper containers | **default** — today’s behaviour (`clusters` alias) |
| `caption_glossary` | glossary list | caption packets | stub until caption pipeline lands |
| `abstract_phrases` | phrases | abstract / frontmatter packets | follow-on |
| `wikipedia` | terms (+ `encyclopedia` payloads) | packets when doing role (c) | ontology + lexicon + packet annotator; prefers `encyclopedia` output when present |

**CLI naming**

- Preferred: `--kg-mappers doc_phrases,caption_glossary,wikipedia`
- Alias: `--kg-links` (legacy). Token `clusters` ≡ `doc_phrases`; `wikidata` may alias into `wikipedia`’s ontology role.

**Default:** `doc_phrases` only (≡ current `--kg-links clusters`).

## 4. Map + assemble (detail of steps 4–5 in §1.1)

```text
0. Ensure packets indexed under document containers (§1.1 / §2.1)
1. Resolve mapper list (--kg-mappers / --kg-links aliases)
2. Optional shared term filter (min n_papers, max_terms) for extracted terms
3. Run each mapper → union nodes/edges by id into **one graph**
4. Optional view-specific passes (e.g. synonym collapse for incidence HTML)
5. Detect disjoint subgraphs (islands); expose for user removal of packets and/or terms
6. Write kg/graph.json, islands.json, kg_summary.json, knowledge_graph.html
```

Params stamped on the summary include `mappers` / `mappers_used` / `mappers_skipped` (and keep `kg_links*` mirrors during the alias period).

**Cleaning:** removing an island may delete **packet** nodes, **term** nodes, or both (plus incident edges). That is the curator loop tying KG display back to corpus retention — same spirit as today’s BKG `clean`, generalized beyond papers-as-only-packets.

## 5. Artifact contracts

### Document mapper (`doc_phrases`)

Inputs (existing):

- `clusters/clusters.json` — paper ids + term weights  
- `phrases/phrases_terms.csv` — ranking by `n_papers`  
- review / `data/metadata/*_metadata.json` — paper titles for tooltips  

### Caption mapper (`caption_glossary`) — contract for “elsewhere”

When present under `--workdir`:

```text
figures/captions.json
```

Suggested shape:

```json
{
  "packets": [
    {
      "id": "fig:PMC123_F1",
      "packet_type": "caption",
      "label": "Figure 1",
      "text": "Caption text …",
      "parent_id": "europe_pmc_PMC123",
      "title": "optional hover title"
    }
  ],
  "glossary": [
    { "phrase": "el niño", "display": "El Niño" }
  ],
  "edges": [
    {
      "phrase": "el niño",
      "packet_id": "fig:PMC123_F1",
      "weight": 1.0
    }
  ]
}
```

- If `edges` are precomputed, the mapper loads them (no search in-repo yet).  
- If only `packets` + `glossary` exist, a later version may run matching here.  
- If the file is missing, the mapper is **skipped** (not an error).

Glossary may also live at `glossary/terms.json` later; v1 of the stub reads glossary from `captions.json` or skips.

## 6. Compatibility

| Today | After generalisation |
|-------|----------------------|
| `kind=paper` node | **paper = container**; UI may still show orange container nodes; packets hang underneath |
| `--kg-links clusters` | alias of `--kg-mappers doc_phrases` |
| `--kg-links clusters,wikipedia` | `doc_phrases` + `wikipedia` mappers (ontology / lexicon / annotate roles) |
| HTML groups Paper / Term | Paper group ≈ container; Caption group when caption packets exist |
| single connected incidence view | one graph file; views may hide homogeneous edges or show disjoint components |

## 7. Non-goals (this cut)

- Replacing phrase extraction  
- Implementing full caption OCR / matching inside this repo  
- Multi-partite viewer (term–packet–wiki as three simultaneous partitions)  
- Changing the one-command tutorial beyond documenting mapper names  

## 8. Related tools and prior art

Useful to compare; we are **not** wrapping these in v1, but they inform the mapper split (match vs assemble vs display).

### A. Lexicon → text span matching (engine for a mapper)

| Tool | What it does | Fit |
|------|----------------|-----|
| [FlashText](https://github.com/vi3k6i5/flashtext) | Fast multi-keyword extract/replace (Aho–Corasick / trie) | Strong candidate inside `caption_glossary` / abstract mappers |
| [spaCy PhraseMatcher](https://spacy.io/api/phrasematcher/) | Match large terminology lists with tokenization | Same role; heavier dependency |
| [merpy / MER](https://github.com/lasigeBioTM/merpy) | Lexicon NER + optional ontology link; returns offsets | Good when glossary is ontology-backed |
| [IAMsystem](https://github.com/scossin/iamsystem_python) | Dictionary entity linking with fuzzy / abbrev support | Noisy captions / OCR-ish text |
| [REL](https://github.com/informagi/REL/) | Wikipedia entity linking + disambiguation | Closer to our encyclopedia resolve than packet search |
| sklearn `CountVectorizer(vocabulary=…)` | Fixed lexicon → document–term matrix | Exact “terms × packets” counts; matrix is already bipartite incidence |

### B. Document–term / bibliometric networks (assemble + view)

| Tool | What it does | Fit |
|------|----------------|-----|
| [bibliometrix `conceptualStructure`](https://github.com/massimoaria/bibliometrix) | Bipartite term–document net → CA/MCA/MDS + clusters | Same graph shape as our BKG; R stack |
| [VOSviewer](https://www.vosviewer.com/) | Term co-occurrence maps from titles/abstracts | Usually **term–term**, not term–document bipartite |
| NetworkX `bipartite` | Build/analyse bipartite graphs | We already use graph libs for clusters |
| KET-RAG (research) | Text-unit ↔ keyword bipartite + KG skeleton for retrieval | Same *shape* at RAG scale; their “chunks” are retrieval units, not our packets |

### C. Figures / captions (packet type = caption)

| Work | What it does | Fit |
|------|----------------|-----|
| Image–term co-occurrence / glossary alignment (e.g. thesis work on multilingual image–term models) | Align terms with images via captions / CBIR | Conceptual cousin of `caption_glossary` |
| Look, Read and Enrich ([paper](https://ar5iv.labs.arxiv.org/html/1909.09070), [code](https://github.com/expertailab/Look_read_and_enrich)) | Figure–caption correspondence learning + KG enrichment | Multimodal; not lexicon search |
| Bipartite image–text association (e.g. Srivastava & Siskind-style random walks) | Linguistic words ↔ visual words | Analogy: glossary ↔ caption packets |

### D. Takeaway for our design

1. **Matching** (lexicon in packet text) is a solved commodity layer — FlashText / PhraseMatcher / CountVectorizer / MER.  
2. **Bipartite assemble + cluster + curator UI** is where this project adds value (BAGIT corpus, clean loops, encyclopedia synonym merge, HTML).  
3. **Caption pipelines** elsewhere should emit our `figures/captions.json` contract (or edges); we optionally swap in FlashText later instead of requiring precomputed edges.  
4. Treat Wikipedia/Wikidata as a **mapper** with ontology + lexicon + annotator roles (not a special non-mapper “transform”).

## 9. Implementation sketch (next)

1. `semantic_corpus/cluster_review/kg_mappers.py` — protocol, registry, `DocPhrasesMapper`, `CaptionGlossaryMapper` stub  
2. Refactor `build_kg` to loop mappers then synonym collapse  
3. CLI `--kg-mappers` + alias; docs/tutorial pointers  
4. Tests: existing KG behaviour preserved; multi-mapper union stays bipartite  
