# Authorship snapshot — 2026-11

**Date:** 2026-11-16  
**Repository:** [semanticClimate/semantic_corpus](https://github.com/semanticClimate/semantic_corpus)  
**Purpose:** Record who owns which long-lived branch work, for credit, merge decisions, and archive notes.  
**Related:** [Branch consolidation audit (2026-09-29)](branches2026_09_29/README.md)

Commit counts below are from `git shortlog` on unique commits vs `main` at the time of this snapshot (non-merge commits). Git identity ≠ legal name; aliases that share an email are noted.

---

## People (Git identities)

| Display / Git name | Email(s) | Notes |
|--------------------|----------|--------|
| **petermr** | peter.murray.rust@googlemail.com | Project lead; pipeline / mainline engineering |
| **EmmaBeni** (Larisa Beni) | lecbeni@mail.austral.edu.ar | Also `emmabeni27` (noreply) |
| **Vrinda-S** | s-vrinda@hotmail.com | Review / tutorials / climate-anxiety corpora |
| **BhatSShreya** | 220242@sdmcujire.in | `shreya` branch; also on `renu` / `tab_fig` |
| **Renu** / **rkclimate20** | swati@nipgr.ac.in | Same person; tip of `renu` as `rkclimate20` |
| **Akalya0818** | 127018004@sastra.ac.in | Internship plant–climate case study |
| **ILAKKYA-S** | ilakkya.bt23@bitsathy.ac.in | Internship AQI docs / dumps |
| **Subhangi Panigrahi** | subhangipanigrahi478@gmail.com | Internship AQI review HTML |
| **Gulam Ajdhani** / **saifnama** | saifnama noreply / 2002gulamajdani@gmail.com | Minimal / empty delta vs main |

Overall commit volume across **all** branches (approximate, `git shortlog -sn --all`): petermr, EmmaBeni, BhatSShreya, Akalya0818, ILAKKYA-S, Vrinda-S, then smaller contributions.

---

## Primary author by branch

Primary = most non-merge commits on `origin/<branch>` that are not already in `main`. Tip author is noted where it differs.

| Branch | Primary author | Also notable | Status / role (Nov 2026) |
|--------|----------------|--------------|---------------------------|
| **main** / **pmr202610** | **petermr** | — | Integration line (`pmr202610` ≈ main) |
| **colab-review-classification** | **petermr** | — | **Merged into main** (2026-11-16); remote closed |
| **larisaBeni** | **EmmaBeni** | Vrinda-S, petermr | Dashboard / LA review stack; do not merge wholesale (bulk PDFs) |
| **conicet** | **EmmaBeni** | Vrinda-S, petermr | CONICET line; largely overlapped with larisa / main |
| **vrinda** | **Vrinda-S** | petermr | Tutorials + climate-anxiety content |
| **renu** | mixed: tip **rkclimate20** (Renu); more unique commits by **petermr** | BhatSShreya | Query tutorial / ocean-heatwaves docs |
| **tab_fig** | **petermr** | BhatSShreya | Ocean heatwaves, PRISMA, citizen prospectus |
| **shreya** | **BhatSShreya** | — | Internship / case-study dump — archive, don’t merge as-is |
| **subhangi** | **Subhangi Panigrahi** | — | Internship — archive |
| **Ilakkya-S** | **ILAKKYA-S** | — | Internship — archive |
| **akalya** | **Akalya0818** | — | Internship — archive |
| **gulamajdhani** | **Gulam Ajdhani** / saifnama | — | Empty / deleted progress — safe to drop |
| **ila** | *(no unique commits; tip petermr)* | — | Fully contained in main — safe to delete |

### Ownership summary

- **Larisa (EmmaBeni):** `conicet`, `larisaBeni`
- **Vrinda:** `vrinda` (and substantial co-authorship on larisa/conicet)
- **Shreya (BhatSShreya):** `shreya`; also contributed on `renu` / `tab_fig`
- **Renu:** tip ownership of `renu` (shared engineering with petermr / Shreya)
- **Internship self-named branches:** Akalya, Ilakkya, Subhangi, Gulam — case studies, not product merges
- **petermr:** `main`, `pmr202610`, `tab_fig`, and (now merged) classification work

---

## How to refresh

```bash
# Unique commits per branch vs main
for b in larisaBeni conicet vrinda renu tab_fig subhangi Ilakkya-S akalya shreya gulamajdhani ila; do
  echo "========== origin/$b =========="
  git shortlog -sn --no-merges origin/main..origin/$b | head -8
  git log -1 --format='tip: %an <%ae> | %s' origin/$b
done

# All-time shortlog
git shortlog -sn --all
```

Update this file (or add `authors_YYYYMM.md`) when branch ownership or merge state changes materially.
