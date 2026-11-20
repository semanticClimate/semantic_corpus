# South Asia — open literature and thesis sources

**Module:** [`repositories`](overview.md)  
**Status:** exploratory note (2026-11-19)  
**Prompt:** [discussions/prompt_2026-11-19_repositories_south_asia_shodhganga.md](../../../discussions/prompt_2026-11-19_repositories_south_asia_shodhganga.md)  
**Related:** corpus ingest hooks — [../corpus/design.md](../corpus/design.md); series — [../../joss_series_strategy.md](../../joss_series_strategy.md)

There is **no single SciELO-style regional portal** for South Asia. Coverage is mostly **national thesis repositories**, **Journals Online** sites, and **university IRs**. Adapters should feed the shared **`corpus` contracts** (stable IDs, BagIt, review table)—not invent a parallel layout.

---

Shodhganga is one of the module’s **three target examples** (with Europe PMC and CONICET)—see [target_examples.md](target_examples.md).

## Candidate focus: Shodhganga

| | |
|--|--|
| **Name** | [Shodhganga](https://shodhganga.inflibnet.ac.in/) (INFLIBNET) |
| **What** | India’s national open reservoir of **PhD theses** (ETDs); very large (600k+ theses reported) |
| **Why for us** | Strong open full-text / metadata target for **personal/project corpora** of South Asian scholarship; aligns with “theses” as a first-class ingest material in `corpus` |
| **Working stance** | **We might work on Shodhganga** as a `repositories` adapter (or harvest recipe) when a volunteer/owner slice is available—same pattern as other GS sources: declarative config, human limits, skip-satisfied ingest into `corpus` |
| **Caveats** | Access/API surface, rate limits, PDF-only quirks, and MoU/membership rules need checking before production harvest; start with small limited pilots and real fixtures |

Any Shodhganga work should use **`corpus` ingest hooks**, not a one-off folder dump.

---

## Other main South Asian sources (map)

### Theses / ETDs

| Country | Source | Notes |
|---------|--------|--------|
| **India** | **Shodhganga** | Primary national ETD target (see above) |
| **India** | etd@IISc, CSIR e-Theses, specialist university IRs | STEM / institutional supplements |
| **Pakistan** | Pakistan Research Repository (HEC) | National PhD thesis archive |
| **Bangladesh** | Open Research Bangladesh + university IRs; DAATJ (agri) | Aggregator + IRs |
| **Nepal / Sri Lanka / Maldives / Bhutan** | University / national-library catalogues | No Shodhganga-scale national ETD portal |

Indexes (not native stores): OATD, NDLTD Global ETD Search, BASE.

### Journals / articles

| Source | Role |
|--------|------|
| BanglaJOL, NepJOL, Sri Lanka Journals Online | National OA journal portals (INASP JOL family) |
| DOAJ | Index; India + Pakistan dominate regional OA journal counts |
| IndiaRxiv | India-focused preprints |
| NDLI / OAR@INFLIBNET | Broader Indian digital library / OA initiatives |
| PakMediNet | Pakistan medical literature visibility |
| Large university IRs | Mixed articles + theses |

---

## Implications for the `repositories` module

1. Prefer **Shodhganga** (and HEC PRR) as thesis-shaped pilots for South Asia.  
2. Expect **IR-by-IR** and **JOL** work for articles—not one Europe PMC–like API.  
3. Partnership rule from series strategy still applies: prefer a **repository + volunteer** when reaching out.  
4. Keep Global South emphasis in JOSS text honest: Latin America adapters exist today; South Asia (starting with Shodhganga) is a **planned expansion**, not yet claimed as shipped.

---

## Next steps (when we pick this up)

- [ ] Confirm public search/download/API or scrape-friendly HTML for a **limited** Shodhganga pilot  
- [ ] Draft declarative YAML + ID stem conventions for ETDs  
- [ ] Wire through `corpus` ingest hooks; review-table QA  
- [ ] Real fixture (small open thesis set); `SC_LIVE_API=1` for live tests only  
- [ ] Owner/volunteer for ongoing adapter maintenance  
