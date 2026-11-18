# User narratives — why `corpus` is needed

**Module:** [`corpus`](overview.md)  
**Audience:** JOSS Statement of need / tutorials  
**Design:** [design.md](design.md)  
**Prompt:** [discussions/prompt_2026-11-18_corpus_user_narratives.md](../../../discussions/prompt_2026-11-18_corpus_user_narratives.md)

Three short, diverse stories from the user’s point of view. Each ends with what breaks without a personal-corpus substrate—and what `corpus` supplies instead.

---

## 1. Amira — sampled literature for a methods paper

I am writing a methods note on ocean heatwaves. I need **about fifty** open full texts from Europe PMC, not the entire hit list. Last year I ran a download script, filled a folder with PDFs, lost track of which IDs already arrived when my laptop slept, and re-downloaded half of them. My co-author could not tell which files were “final.”

I need a **project tree I can interrupt and resume**: a declarative query with a limit, a BagIt (or equivalent) layout with stable IDs, and a rerun that **skips what already succeeded**. I also need a simple table to browse and delete off-topic papers before I cite the bag in the paper.

**Without `corpus`:** ad-hoc folders, opaque restart behaviour, no shared layout for co-authors or later KG/export tools.  
**With `corpus`:** human-limited ingest, skip-satisfied `doit`-style reruns, review table, citable personal corpus.

---

## 2. João — a closed set of IPCC volumes

My group is annotating **specific** IPCC Working Group and Special Report PDFs—a finite list, not a search API. The files are large; conversion to usable HTML fails on some volumes the first time. We improve the cleaner pack and must **reprocess overlays** without pretending the originals changed.

I do not want an institutional repository. I want a **personal/project filestore** that treats the closed set as first-class, stops cleanly when I kill the job, resumes the rest, and semanticises chapters into sections, paragraphs, and figure/table captions with IDs we can quote.

**Without `corpus`:** one-off conversion scripts per volume, no skip/resume contract, no stable chunk IDs for the whole set.  
**With `corpus`:** closed-set ingest, BagIt as source of truth, declarative cleaners, software-driven Rerun for semantic overlays.

---

## 3. Priya — Zotero for discovery, corpus for the project artefact

I already use **Zotero** offline to find and read papers and keep PDFs attached. That works for bibliography. It does **not** give my internship team a preservation-oriented project bag, declarative HTML cleaning, or a layout that our phrase/KG and chatbot export tooling can consume by contract.

I want to keep Zotero as my **bibliographic search and reading** tool, then push a chosen collection into `corpus` so the **project artefact** is a BagIt tree plus semantic HTML I can curate in a review table and hand to the next module.

**Without `corpus`:** either we reimplement analysis on top of Zotero’s SQLite model, or we dump attachments into yet another undocumented folder.  
**With `corpus`:** Zotero interoperates as a source; `corpus` owns the personal-corpus substrate (BagIt, clean/semanticise, incremental ingest, review UI).

---

## How these map to the Statement of need

| Narrative | Problem | Audience slice | Gap filled by `corpus` |
|-----------|---------|----------------|------------------------|
| Amira | Bounded OA harvest that must resume | Domain researcher / methods author | Limited query ingest + skip-satisfied rerun + review QA |
| João | Finite grey/report PDFs + re-clean | Project / assessment team | Closed-set filestore + declarative semanticisation |
| Priya | Discovery tool ≠ project corpus | Zotero-centred user + downstream modules | Interop ingest + BagIt/semantic contracts |

See also usage scenarios A–F in [design.md](design.md) §3.
