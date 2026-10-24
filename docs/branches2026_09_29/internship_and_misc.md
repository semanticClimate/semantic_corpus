# Internship and miscellaneous branches

**Verdict summary:** mostly **do not merge wholesale** into `main`. Archive thin samples if needed, then delete remotes.

---

## `Ilakkya-S` — archive only

- **Ahead 27 / behind 30**
- Personal AQI project under `docs/ILAKKYA_S/`: review tables, PRISMA image, XML sample DB, **large** `VIDEO_AQI.mp4`, zip
- **Useful fragment:** curated `review_table*.csv/json` + short README — optional copy to `docs/internship_archive/ilakkya_aqi/`
- **Do not merge:** video, zip, full XML dump

---

## `akalya` — archive only

- **Ahead 7 / behind 30**
- `docs/akalya_project/` plant–climate papers (PDF/XML) + `query_configuration.md` + review CSV
- Note: `origin/main` recently **deleted** many `corpora/akalya_project` XMLs — do not reintroduce bulk
- **Useful fragment:** `query_configuration.md` + README only

---

## `shreya` — archive / thin sample

- **Ahead 38 / behind 30**
- Global warming / temperature-rise query, review editor HTML, daily progress, prisma image, many XML files under `corpora/shreya_project/`
- **Useful fragment:**
  - `scripts/build_shreya_review_table.py` (if not already via `tab_fig`)
  - `review_table_editor.html` as a UX sample
  - curated review CSV/JSON
- **Do not merge:** full PMC XML tree

---

## `subhangi` — partial / cleanup

- **Remote ahead 7 / behind 0** relative to `main`
- AQI review HTML under `corpora/subhangi_project/`
- Pollutes history with **`__pycache__/*.pyc`** — strip if anything is taken
- **Local-only** tip `f39600c` (*prototyped Prisma diagram*): PRISMA modules + `docs/prisma_flow.md` + ORAT draft — **but equivalent PRISMA code is already on `tab_fig`/`renu`**; prefer those, then drop local tip

---

## `gulamajdhani` — delete

- **Ahead 2 / behind 37**
- Created then deleted `progress_report.md` / `ai_drug_corpus` — **no remaining useful file delta**
- Safe to delete remote branch

---

## `ila` — delete

- **Ahead 0 / behind 30**
- Tip equals old `main` point (`23d16a9`); nothing unique
- Safe to delete remote branch

---

## Local `main` hygiene

Local `main` @ `23d16a9` is **30 commits behind** `origin/main`. Before consolidation PRs:

```bash
git checkout main
git pull origin main
```

Those 30 commits are largely deletions of `corpora/akalya_project` artefacts — aligning local `main` avoids resurrecting deleted blobs when merging feature branches.
