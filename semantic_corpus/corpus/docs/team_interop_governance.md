# Team interop governance — “guidelines then harvest”

**Date:** 2026-11-20  
**Home:** `corpus/` (core module / shorthand for this repository’s interface surface)  
**Audience:** dispersed volunteer owners of submodules (`repositories`, `phrases_kg`, encyclopedia, chatbot)  
**Prompt:** [discussions/prompt_2026-11-20_coar_force11_codata_parallel.md](../../../discussions/prompt_2026-11-20_coar_force11_codata_parallel.md)  
**Related:** [design.md](../../../docs/modules/corpus/design.md) · [siblings.md](../../../docs/modules/corpus/siblings.md) · [`MODULE_SPEC.md`](../../MODULE_SPEC.md) · [joss_series_strategy.md](../../../docs/joss_series_strategy.md)

**Role of `corpus/`:** this core defines the **interfaces** submodules must honour (BagIt layout, paper IDs, review-table vocabulary, ingest hooks, semantic HTML contracts). Submodules implement against those interfaces; they do not invent parallel dialects.

This note expands the social parallel: **COAR / LA Referencia / OpenAIRE–style “guidelines then harvest”**, and how it maps onto a young, geographically dispersed, AI-assisted team that already touches **FORCE11** and **CODATA** communities.

---

## 1. What “guidelines then harvest” means in the repository world

Large open-science networks do **not** start by letting every institution invent a private layout and hoping federation works later. They invert the order:

| Step | What the network does | Example |
|------|------------------------|---------|
| **1. Agree guidelines** | Small, shared metadata/behaviours; persistent IDs; access rights; funding links; controlled vocabularies | [OpenAIRE Guidelines](https://guidelines.openaire.eu/); COAR controlled vocabularies / [Next Generation Repositories](https://coar-repositories.org/next-generation-repositories/) behaviours |
| **2. Expose for harvest** | Each node implements OAI-PMH (or equivalent) *against the guideline*, not a one-off dump | National IR nodes, SciELO/Redalyc-class platforms |
| **3. Validate** | Machine checks before “you are in the network” | OpenAIRE Validator; LA Referencia quality rules |
| **4. Harvest / aggregate** | Central or federated indexes collect **compliant** records | OpenAIRE graph; [LA Referencia](https://www.lareferencia.info/) regional search |
| **5. Link to full text at source** | Aggregator often holds **metadata + links**; bitstreams stay at the home repository | LA Referencia → CONICET / university IR (see [`repositories/docs/latin_america.md`](../../repositories/docs/latin_america.md)) |

**Social content of the pattern:** interoperability is a **community contract** first, software second. Implementations (DSpace, custom scrapers, national portals) may differ; the **guideline** is what makes harvest possible.

That is the opposite of “each volunteer ships a clever module and we reconcile interfaces later.”

---

## 2. FORCE11 and CODATA — why they matter for *our* parallel

Our project already sits near communities that preach the same order of operations: **principles and shared artefacts before local tooling**.

### FORCE11

FORCE11 (Future of Research Communications and e-Scholarship) is where much of the modern **scholarly communication reform** vocabulary was forged and debated: open citation, FAIR-adjacent practice, software/data as first-class research objects, community-authored principles.

**Parallel for us:**

- Treat **`corpus/` interfaces** and module boundaries like **community principles**: short, citable, versioned in git (ADRs / `MODULE_SPEC` / BagIt + ID vocabulary).  
- Weekly meetings play the role of a miniature FORCE11 working group: **accept** a guideline (or reject it), then submodule implementations follow.  
- AI-written code is allowed to *implement* accepted interfaces; it must not silently invent a competing vocabulary (same failure mode as a repository that ignores OpenAIRE profiles).

### CODATA

CODATA (Committee on Data of the International Science Council) focuses on **data policy, stewardship, and international coordination**—standards, FAIR practice, cross-domain data that can be found and reused.

**Parallel for us:**

- Our “data” for interop is the **personal corpus artefact** owned by `corpus/` (BagIt tree, review table, semantic HTML chunks, declarative pilots)—not only journal PDFs.  
- CODATA-style thinking says: define **what must be present for reuse** (IDs, provenance hooks, licenses, machine-readable metadata) before scaling harvest.  
- Submodule owners are stewards of a **slice of the graph** (repositories → corpus → phrases_kg → encyclopedia/chatbot), analogous to domain stewards under a shared data policy whose hub contract is `corpus/`.

FORCE11 leans **communication & objects**; CODATA leans **data policy & stewardship**. Together they reinforce: **agree the contract in the open community, then automate compliance**.

---

## 3. `corpus/` as interface hub; submodules as nodes

| Network practice | Our practice |
|------------------|--------------|
| OpenAIRE / COAR **guidelines** | Interfaces owned by **`corpus/`**: BagIt layout, paper IDs, review columns, ingest hooks, semantic HTML; plus `MODULE_SPEC` / `module.yaml` / coding_style §0 |
| **Validator** before aggregation | pytest + CI on real fixtures; import/boundary checks; schema validation of pilots and review rows |
| **Harvest** only compliant sources | `repositories` adapters / profiles that emit **corpus** contracts; reject parallel BagIt dialects |
| Federated search, full text at source | LA Referencia-style discovery vs CONICET/USP bitstreams; EPMC as API-full-text exception |
| National nodes + regional hub | Submodule owners (Larisa, Neel/Anusha, …) + **`corpus/` hub** (Renu / weekly meeting with PMR) |
| Versioned community docs | `discussions/` transcripts + `corpus/docs/` and `docs/modules/corpus/`; prompts archived for JOSS/AI disclosure |

**Guideline / interface owners (`corpus/` hub):** weekly call accepts interface changes.  
**Node owners (submodules):** implement and test against `corpus/` interfaces; may use AI heavily *inside* the node.  
**Harvest (integration):** only paths that pass contract tests land on `main` / demos.

---

## 4. What we tell volunteers (and their AIs)

1. **Do not start with a new folder layout.** Start from the accepted **`corpus/`** contracts.  
2. **Guidelines are small and boring on purpose** — like OpenAIRE’s “lowest technical barrier” metadata profiles.  
3. **If the AI invents a field**, either add it to a `corpus/` interface via the weekly meeting or delete it.  
4. **Compliance is tested**, not trusted — mirrors OpenAIRE Validator before aggregation.  
5. **FORCE11/CODATA language is welcome in JOSS text**: FAIR-ish personal corpora, community governance, software as a research object—grounded in our actual BagIt + declarative ingest story.

---

## 5. What this is *not*

- Not a claim that we *are* OpenAIRE or LA Referencia.  
- Not a requirement to implement OAI-PMH tomorrow.  
- Not a substitute for FORCE11/CODATA membership paperwork—only a **governance metaphor** and alignment story for dispersed contributors.

---

## 6. Near-term artefacts that make the parallel real

| Artefact | Role |
|----------|------|
| Accepted ADRs + `corpus/` design docs | Our “guidelines” / interface surface |
| Schemas for pilots / review rows / search hits | Machine-checkable profiles |
| Contract pytest + CI | Validator |
| `import-linter` (or similar) | Submodules must not bypass `corpus/` contracts |
| Submodule `docs/` source lists | Domain knowledge (LA, South Asia) without forking layout |
| Weekly acceptance of interface PRs | Social harvest gate |

---

## 7. One sentence for the team

**Like COAR, LA Referencia, and OpenAIRE—and in the spirit of FORCE11 and CODATA—`corpus/` publishes small shared interfaces first; we validate submodule compliance automatically, and only then “harvest” volunteer work into the shared corpus graph; local AI coding is welcome inside those constraints, not instead of them.**
