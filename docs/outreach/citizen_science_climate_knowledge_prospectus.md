# Prospectus: Citizen Science Climate Knowledge

**Working title:** *Local Climate Knowledge — tools citizens can trust*  
**Date:** 2026-09-22 (system date of generation)  
**Status:** Draft for engagement with councils, voluntary groups, educators, and community partners  
**Built on:** [#semanticClimate](https://semanticclimate.github.io/) open tools and materials

---

## 1. The invitation

Climate decisions are made locally — in council chambers, neighbourhood meetings, school halls, and charity boards — but the best evidence often sits in PDFs, paywalled journals, and 10,000-page reports.

**Citizen Science Climate Knowledge** is an interactive toolkit that helps ordinary people and civic groups build a **small, trustworthy knowledge base** on a precise climate topic they care about.

Examples:

| Local concern | Knowledge base you could build |
|---------------|--------------------------------|
| Flooding after heavy rain | *Urban floods in Europe* |
| Young people’s mental health | *Climate anxiety* |
| Summer heat in cities | *Urban heat islands and health* |
| Coastal erosion | *Sea-level rise and coastal communities* |
| Allergies and air | *Pollen, pollution, and climate* |

You choose the topic. The tools help you gather **open scholarly literature** and **material from trusted authorities** (such as the IPCC), clean it, extract the key ideas, organise an encyclopedia, and ask questions of a **local AI assistant** that answers from *your* sources — not the open internet.

The same toolkit can run **online** (shared workshop, public demo) or **offline on a laptop** (village hall, school without reliable Wi‑Fi, confidential local work).

---

## 2. Who this is for

We designed the prospectus language for several audiences at once. Each gets a clear benefit.

### Local councillors and council officers

- Briefings grounded in cited evidence, not social-media summaries  
- A **reproducible trail**: which papers and reports were included, which were excluded, and why  
- Something you can show residents: “here is how we checked”

### Voluntary groups, NGOs, and faith or community organisations

- Campaign and education materials tied to real sources  
- Workshops where members help *curate* what goes into the knowledge base  
- No requirement to become data scientists — roles for readers, note-takers, and topic experts

### Teachers, libraries, and adult learning

- Project-based learning: pick a local climate question, build a mini-corpus, present findings  
- Open tools and open literature where possible  
- Online or classroom laptop modes

### Journalists, researchers, and civic tech people

- Transparent pipeline from search → curated corpus → encyclopedia → local Q&A  
- Exportable artefacts (review tables, manifests, encyclopedias) for reuse  
- Compatible with existing #semanticClimate and open-science practice

### Young people and citizen scientists

- Hands-on contribution: reviewing papers, tagging keyphrases, writing plain-language encyclopedia entries  
- Skills that transfer (critical reading, evidence, digital literacy)  
- Belonging to an international open community (#semanticClimate)

---

## 3. What “trustable” means here

Citizens are right to be wary of chatbots that invent answers. This project treats **trust as a design feature**, not a slogan.

| Principle | What you get |
|-----------|----------------|
| **Named sources** | Answers cite papers, IPCC chapters, or other included documents |
| **Human curation** | People decide what is in / out of the corpus (review table) |
| **Open literature first** | Prefer open-access scholarly work and public authority reports |
| **Bounded AI** | The local assistant retrieves from *your* knowledge base, not the whole web |
| **Reproducible steps** | Search queries, dates, and review decisions can be saved and revisited |
| **Offline option** | Sensitive or poorly connected settings need not send data to a cloud chatbot |

Trust is strongest when the knowledge base is **small and precise** (one locality, one hazard, one community concern) rather than “everything about climate.”

---

## 4. How it works (simple story)

```text
Search  →  Corpus  →  Clean  →  Keyphrases  →  Encyclopedia  →  Local LLM
```

1. **Search** — Define a focused question (e.g. urban floods in Europe). Search open scholarly repositories and/or trusted report collections.  
2. **Corpus** — Download and keep a manageable set of documents (often tens of papers, not thousands).  
3. **Clean** — Convert and normalise text (HTML/XML where possible) so tools can read it reliably.  
4. **Keyphrases** — Extract candidate terms and concepts; people refine what matters for *this* place and topic.  
5. **Encyclopedia** — Build short, linked entries: definitions, context, pointers back into the corpus.  
6. **Local LLM** — Ask questions in plain language; answers come with citations from the curated set.

Much of this pipeline already exists across #semanticClimate repositories (search/download, review, encyclopedia, IPCC HTML corpora, RAG chat). This prospectus is about **packaging it for citizens** — clearer roles, friendlier entry points, and both online and offline use.

---

## 5. Two ways to use it

### A. Served online

- Shared workshop or public demo (browser-based)  
- Useful for councils, conferences, and classrooms with Wi‑Fi  
- Can use a temporary public link for a time-limited event  

### B. Local / offline

- Runs on a laptop or small local machine  
- Corpus and encyclopedia stay on disk  
- Local language model for Q&A without sending questions to a remote service  

Same workflow; different deployment. Groups choose what fits privacy, connectivity, and skill level.

---

## 6. What a first project looks like (90-day sketch)

| Phase | Citizen activity | Typical output |
|-------|------------------|----------------|
| **Weeks 1–2** | Agree the precise question and geography | One-page brief + search query |
| **Weeks 3–4** | Search open literature; download a pilot corpus (~30–50 items) | Corpus folder + search record |
| **Weeks 5–6** | Group review: include / exclude / note | Review table; agreed inclusions |
| **Weeks 7–8** | Extract keyphrases; draft encyclopedia entries in plain language | Wordlist + 20–50 entries |
| **Weeks 9–10** | Connect local Q&A; try community questions | Working demo (online or offline) |
| **Weeks 11–12** | Present to stakeholders; decide what to publish or keep local | Short report + live session |

Example starter topics already explored in related work: *climate anxiety*, *ocean heatwaves / ocean currents*, *air quality*, IPCC chapter encyclopedias.

---

## 7. What already exists (honest inventory)

#semanticClimate and sibling projects have already built pieces of this stack:

| Need | Existing capability (examples) |
|------|--------------------------------|
| Literature search & download | `pygetpapers`, `semantic_corpus` (e.g. Europe PMC and other open sources) |
| Human review of what to keep | Interactive HTML review tables |
| Authority corpora (IPCC) | HTML/semantified IPCC materials in public GitHub corpora |
| Keyphrases & dictionaries | `txt2phrases`, encyclopedia / dictionary tooling |
| Encyclopedia browsing | Encyclopedia tools and demos |
| Chat with citations | ClimateInsight / RAG-style assistants over a curated manifest |
| Community practice | Internships, datathons, open documentation |

**Gap this prospectus addresses:** turn the toolkit into a **citizen-facing product and process** — with roles for non-specialists, packaging for councils and voluntary groups, and clear online/offline playbooks.

---

## 8. What we ask of partners

We are looking for early partners, not only users.

| Partner type | How you can engage |
|--------------|--------------------|
| **Council or combined authority** | Pilot one local topic (flood, heat, air); host a workshop |
| **Voluntary / community group** | Co-design the question; supply lived experience and review time |
| **Library, school, or college** | Run a supervised student or public project |
| **Funders and civic funders** | Support packaging, accessibility, and offline kits |
| **Researchers and civic tech** | Harden tools, documentation, and evaluation of trust |

In return, partners get a branded pilot knowledge base, training materials, and open artefacts they can keep.

---

## 9. Ethics and care

- Prefer **open** and **citable** sources; record licences where known.  
- Do not claim the tool replaces professional advice (planning, medical, legal).  
- Be careful with topics that affect mental health (e.g. climate anxiety): pair with appropriate local support resources.  
- Respect privacy: offline mode exists for a reason.  
- Credit community contributors as authors of the knowledge base, not only technicians.

---

## 10. Call to action

If you are a councillor, voluntary group, teacher, librarian, journalist, or citizen who wants **climate knowledge you can check**, we invite you to:

1. **Reply with a precise topic** you care about (one sentence + place if possible).  
2. **Join a short discovery call** to see whether a 90-day pilot fits.  
3. **Co-host a workshop** (online or in person) to build the first corpus together.

Contact and collaboration channels will follow #semanticClimate community practice (open repos, documented workflows, public demos where appropriate).

---

## 11. One-line pitch (for leaflets and email subject lines)

> **Build a small, local, citable climate knowledge base — from open literature and trusted reports — that citizens can question online or offline.**

---

## Appendix A — Audience elevator pitches (30 seconds)

**Councillor:** “We’ll help your team assemble open papers and IPCC-grade sources on one local risk, review them together, and leave you with a cited Q&A tool you can show residents.”

**Voluntary group:** “Your members help decide what counts as evidence for your campaign. The AI only answers from what you approved.”

**Teacher / librarian:** “A project where learners search, read, curate, and explain — then ask a local assistant that must show its sources.”

**Citizen scientist:** “You don’t need to code to start. You need curiosity, careful reading, and a topic that matters where you live.”

---

## Appendix B — Technical backbone (for partners who ask)

High-level mapping to existing #semanticClimate / sibling software (names may evolve):

```text
Search/corpus     →  semantic_corpus / pygetpapers (+ IPCC HTML corpora)
Clean/enrich      →  amilib / amclimate-style conversion and annotation
Review            →  interactive review tables
Keyphrases        →  txt2phrases / docanalysis
Encyclopedia      →  encyclopedia tooling + Wikidata/Wikipedia enrichment where appropriate
Local LLM / RAG   →  ClimateInsight-style ingest + local model; optional tunnel for online demos
```

Detailed runbooks and demo corpora (e.g. ocean heatwaves, climate anxiety) live in project documentation and public GitHub organisations (`petermr`, `semanticClimate`).

---

## Appendix C — Related public materials

- [#semanticClimate site](https://semanticclimate.github.io/)  
- IPCC HTML corpora and cleaned content (e.g. `ipcc_corpus`, `semanticClimate/ipcc`, `amilib` test resources)  
- Encyclopedia and internship guides on the #semanticClimate site  
- This repository’s demo and outreach docs under `docs/`

---

*This prospectus is an engagement document. It is not a funding bid, legal advice, or a claim that any single demo is production-ready for statutory decision-making without further evaluation.*
