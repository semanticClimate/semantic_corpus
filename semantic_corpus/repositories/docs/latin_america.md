# Latin America — open scholarly / scientific repositories

**Module:** `repositories`  
**Date:** 2026-11-20  
**Prompts:** [discussions/prompt_2026-11-20_module_docs_folders.md](../../../../discussions/prompt_2026-11-20_module_docs_folders.md)  
**Related:** [south_asia.md](south_asia.md) · targets EPMC · CONICET · Shodhganga in [`docs/modules/repositories/target_examples.md`](../../../../docs/modules/repositories/target_examples.md)

We already treat as first-class: **SciELO**, **Redalyc**, **CONICET**, plus IR adapters (UBA, USP, UNAL, UNAM, UChile, Kerwa, …).

---

## 1. Most important sources (beyond SciELO / Redalyc / CONICET)

### Regional / multi-country (highest leverage)

| Source | Role |
|--------|------|
| **[LA Referencia](https://www.lareferencia.info/)** | Federated IR network (~12 countries, hundreds of institutions, millions of records). Best regional “map of maps” for national repository aggregates (articles, theses, reports). |
| **[AmeliCA](https://amelica.org/)** | Diamond OA journal infrastructure (with Redalyc / CLACSO / UNESCO); non-commercial OA publishing stack. |
| **[Latindex](https://www.latindex.org/)** | Catalogue/directory of Ibero-American journals (discovery/quality filter more than a full-text store). |
| **[CLACSO](https://www.clacso.org.ar/)** virtual library / repository | Large social-sciences OA collection across LAC networks. |
| **LatinRev** | SSH journal index for the region (visibility; not a single PDF API). |

SciELO + Redalyc remain the two dominant **journal full-text** networks; **LA Referencia** is the dominant **repository federation**.

### Important national / institutional layers

Often harvested via LA Referencia or as standalone DSpace/OJS sites:

| Country | Notable nodes |
|---------|----------------|
| **Brazil** | SciELO Brasil; Oasisbr / IBICT national aggregation; large university IRs (e.g. **USP**) |
| **Mexico** | Redalyc (UAEM); **UNAM** IRs; SciELO México |
| **Argentina** | **CONICET** Digital; university IRs (e.g. **UBA**); SciELO Argentina |
| **Colombia** | National / university IRs (e.g. **UNAL**); SciELO Colombia |
| **Chile** | University IRs (e.g. **UChile**); SciELO Chile |
| **Costa Rica / Central America** | e.g. **Kérwá** (UCR) and similar national university IRs |
| **Peru, Ecuador, Uruguay, …** | National OA IR policies + university DSpace instances (often in LA Referencia) |

### Practical priority for this module

1. Keep **SciELO / Redalyc / CONICET** as exemplars (CONICET is one of the three JOSS targets).  
2. Consider **LA Referencia** (or one national node behind it) as a regional harvest *front door* for discovery.  
3. Treat AmeliCA / Latindex / CLACSO as journal/discovery complements rather than Europe PMC–like download APIs.  
4. Continue IR adapters (USP, UNAM, …) for full-text when the federation only returns links.

---

## 2. Does LA Referencia provide theses themselves?

**Mostly a discovery / metadata layer, not a full-text store.**

LA Referencia **harvests metadata** (via national nodes / OAI-PMH) from member institutional repositories—including articles and master’s/PhD theses—validates it, and offers a **unified search**. For the PDF/XML itself it **points to the original IR** (“access to full text … within the original institutional repository”).

For `repositories` → `corpus`:

| Layer | Role |
|-------|------|
| LA Referencia | Regional search index / records + links (IDs, landing URLs) |
| CONICET, USP, UNAM, … | Where many bitstreams actually live |
| Pipeline pattern | Search LA Referencia → resolve landing/bitstream at home repo → download into BagIt |

Do **not** assume a single LA Referencia bulk full-text API like Europe PMC.
