# Structure → semantic_corpus migration plan

**Date:** 2026-07-15 (system date)  
**Status:** Agreed plan — documentation only (no migration code yet)  
**Sibling project:** `../structure`  
**Related:** [orat_plan.md](orat_plan.md), [development_plan.md](development_plan.md), `../structure/docs/`

---

## Decision summary

1. **Paper-structure belongs in the semantic_corpus product story** (harvest → BAGIT → transform/structure → review).
2. **Omit Hindi / KrutiDev** from this merge plan — not in current scope.
3. **Docling is optional:** if it loads and runs, use it; otherwise skip with an explicit status. Core corpus (search, download, BAGIT, review, PRISMA) must never require Docling.
4. Prefer a **phased move** (contract → optional integration → migrate paper-structure code) over a blind full-repo dump.

---

## Why merge (pros)

| Pro | Why it matters |
|-----|----------------|
| Closes planned gaps | PDF→HTML, structure detection, and semantification are already on the semantic_corpus roadmap |
| One pipeline | Query → download → BAGIT → structured HTML → review / PRISMA / encyclopedia |
| Shared corpus contract | One layout for `data/documents/` and structure outputs under `data/semantic/` or `analysis/structure/` |
| Easier onboarding | One clone for ORAT / review plus structure pilots |
| Ends path hacks | Today `structure` hardcodes sibling `../semantic_corpus` paths |
| Version alignment | Corpus HTML conventions and extractors ship together |

---

## Cons and mitigations

| Con | Mitigation |
|-----|------------|
| Docling is heavy (PyTorch, models) | Optional extra + runtime try/import; default install stays light |
| CI cost if every job installs Docling | Core CI without Docling; one optional job with extras |
| Two HTML stories (JATS `xml_to_html` vs Docling) | Document fallback chain; prefer JATS when XML exists |
| Git history / import churn | Phased move; keep package boundaries clear |
| Downstream siblings (chatbot, etc.) | Point them at optional extra or a thin shim |

---

## Scope lock

### In scope for semantic_corpus

- Docling PDF → HTML **when available**
- HTML validation of conversion output
- Paper pilots (abstract / table / JATS alignment against BAGIT corpora)
- Wiring into corpus dirs (`documents/` → `semantic/` or `analysis/structure/`)

### Out of scope (this plan)

- Hindi / Kruti Dev / annual-report font pipelines  
  (remain in `../structure` or elsewhere until explicitly revisited)

---

## Docling policy: optional progressive enhancement

| Situation | Behaviour |
|-----------|-----------|
| Docling **imports** successfully | May use PDF → HTML / structure pilots |
| Import **fails** or not installed | **Skip** Docling; do not crash core CLI or install |
| User requests a Docling-only op without it | Clear message: not available; install optional extra or use JATS/XML→HTML |
| Core corpus workflows | **Never** require Docling |

Prefer both:

- **Packaging:** `optional-dependencies` e.g. `[docling]` or `[structure]`
- **Runtime:** `try/except ImportError` (or equivalent) with logged skip

### Fallback chain (when Docling is skipped or fails)

1. Prefer existing **JATS/XML → HTML** (`semantic_corpus.transformation.xml_to_html`) when XML exists.  
2. If only PDF and no Docling → mark `structure_status: unavailable` (do not invent empty HTML).  
3. Record per-paper status: `docling | jats_html | unavailable | failed`.

### Non-negotiables for “ignore”

- Do **not** fail silently mid-batch: log Docling skipped / failed.  
- Summarise corpus jobs: *N converted with Docling, M skipped, K failed*.  
- Never pretend Docling HTML exists if it was skipped.

---

## Known Docling problems (why optional)

### Cannot load (install / import)

- Heavy stack (PyTorch, Docling, related binaries); slow/large installs.  
- Missing without optional extras → import fails.  
- Local directory named `docling/` can shadow the package (`ModuleNotFoundError`).  
- Constrained environments may not install binary wheels.

### Cannot run (environment / startup)

- First run downloads layout models (Hugging Face): needs network, disk, time.  
- Offline / blocked network → unusable after install.  
- High RAM/CPU demand.  
- OCR backends fragile (missing extras → RapidOCR/torch errors); OCR often disabled by default in structure.

### Run fails (hard errors)

- OCR/config mis-set → abort.  
- Corrupt, encrypted, or awkward PDFs → failed or empty output.  
- Behaviour can change across Docling versions (pin version; hash outputs).  
- Partial writes → no trustworthy HTML artefact.

### Runs but quality is wrong (soft failure)

- Bad reading order (e.g. Elsevier multi-region title pages).  
- Conversion artefacts (lists, headings, tables) — structure has validators for these.  
- Typography noise (spaced headings, footer/sidebar bleed).  
- Weaker than JATS when both exist (pilots: Docling PDF track often behind corpus HTML/JATS).  
- Output is a **draft**, not final semantic structure.

### Long runtimes / cost

- Cold start (model download + load) before first PDF.  
- Per-PDF conversion in the minutes class; OCR much slower.  
- Corpus-scale batches are long; cache and reuse converted HTML.  
- Accurate table modes trade time for quality.

**Implication:** Docling is best-effort enrichment, never on the critical path for harvest, review, or PRISMA.

---

## Migration phases

### Phase 0 — Scope lock (done in this doc)

- In: paper structure + optional Docling.  
- Out: Hindi.  
- Policy: Docling optional at packaging and runtime.

### Phase 1 — Contract (can stay sibling briefly)

- Explicit `--corpus-dir` / `--query-dir` (no sibling path assumptions).  
- Output under corpus: e.g. `data/analysis/structure/` or `data/semantic/`.  
- Per-paper `structure_status` as above.  
- **Gate:** climate_anxiety (or equivalent) pilot runs with explicit paths only.

### Phase 2 — Optional integration

- semantic_corpus facade calls structure APIs when present.  
- Runtime detection of Docling; optional `[docling]` / `[structure]` extra.  
- **Gate:** review / ORAT docs mention structure as optional step.

### Phase 3 — Move paper-structure code into semantic_corpus

- Import history (subtree / filter-repo) into e.g. `semantic_corpus/structure/` or `document_structure/`.  
- Style: absolute imports, empty `__init__.py`, pygetpapers/amilib guides.  
- Core tests green **without** Docling; Docling tests via `importorskip` or a separate CI job.  
- Archive or slim `semanticClimate/structure` for leftovers outside this scope.  
- **Gate:** one PMC PDF→HTML→validate in BAGIT when Docling installed; JATS path works without it.

### Phase 4 — Unify document views

- Tutorials: “HTML from JATS when XML exists; Docling PDF path when installed.”  
- Later: review UI / PRISMA may show structure availability without requiring Docling.

### Phase 5 — Deprecate sibling (time-boxed)

- Dual maintenance for 1–2 release cycles.  
- Update chatbot / ORAT / amilib docs to new import paths.  
- Hard-archive old paper-structure surface in the sibling repo.

---

## Packaging sketch (not implemented yet)

```text
pip install -e .                  # core: harvest, BAGIT, review, PRISMA, xml_to_html
pip install -e ".[docling]"       # or .[structure] — enables PDF→HTML when hardware/network allow
```

Runtime: if Docling cannot be imported or first-run models cannot load, skip and continue with JATS/unavailable status.

---

## Go / no-go criteria

| Prefer phased merge | Prefer keep sibling longer |
|---------------------|----------------------------|
| ORAT/corpus need PDF structure soon | Almost all users only harvest + review |
| Tired of dual checkouts and path hacks | Even optional Docling CI is unacceptable |
| Paper-structure is the main future of `structure` | Separate release cadence is essential |

**Current recommendation:** proceed with **Phases 0–2 immediately** (docs + contract + optional wiring plan); execute **Phase 3** after Phase 1 gate passes.

---

## Explicitly deferred

- Implementing the move or adapter code (await separate approval).  
- Hindi / KrutiDev migration.  
- Making Docling a hard core dependency (rejected).
