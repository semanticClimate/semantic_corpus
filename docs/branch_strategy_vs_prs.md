# Personal branches vs pull requests

**Audience:** mentors and early-career researchers (ECRs) in the semanticClimate / `semantic_corpus` developer community  
**Context:** short stays (~3 months), often little prior collaborative software experience; weekly review sessions; personal branches rather than PR-gated workflow as the default  
**Date:** 2026-11-16

---

## Verdict for this setting

Personal branches plus weekly review fit a 3‑month ECR cohort better than a PR‑gated workflow as the *default*. Use light PR habits only when someone is changing shared `main` product code.

---

## Personal branches (current practice)

### Benefits

- **Low ceremony** — ECRs can commit and push without learning GitHub review UI, CI gates, or rebase etiquette in week 1.
- **Matches the work shape** — short projects are often *case studies* (query → review table → notes), not long-lived product features; a named branch is a natural “lab notebook.”
- **Fits weekly review** — the human gate is the live session: demo the branch, then a mentor salvages or merges. That replaces asynchronous PR review.
- **Psychological safety** — feedback stays in the session rather than a public “requested changes” thread.
- **History of experiments** — messy corpora, zips, and scratch trees can stay off `main` until someone deliberately lifts thin leftovers.

### Downsides

- **Stale sprawl** — branches drift tens of commits behind `main`; closing them becomes archaeology.
- **No forced small diffs** — uploads, `__pycache__`, video/zip, and nested bags land on the branch and feel permanent.
- **Merge cost lands on mentors** — conflicts, tip-vs-main uniqueness checks, and selective path checkout instead of a clean PR.
- **Weak shared norms** — without a PR checklist, people do not reliably learn “don’t commit `temp/` / binaries / secrets.”
- **Discoverability** — work is invisible unless someone knows the branch name; there is no open-PR list as a dashboard.
- **Credit vs integration blur** — authorship of a branch is not the same as “this is product.”

---

## Pull requests

### Benefits

- **Teachable collaboration skill** — description, small commits, respond to comments — useful beyond the internship.
- **Review before it hits `main`** — CI, lint, and rules such as “no corpora in this change” are enforceable.
- **Audit trail** — discussion tied to the change; easier handoff when the person leaves at 3 months.
- **Natural close** — merged PR → delete branch; fewer zombie remotes.

### Downsides for this cohort

- **Front-loaded complexity** — fork/PR/rebase/conflict resolution burns scarce weeks.
- **Async review lag** — if mentors mainly meet weekly, PRs sit open and block, or get rubber-stamped and lose the benefit.
- **Wrong tool for dumps** — a hundreds-of-files corpus PR is worse than a personal branch that will never merge wholesale.
- **Can chill experimentation** — fear of failing CI or looking inexperienced.

---

## Hybrid that matches this community

| Work type | Prefer |
|-----------|--------|
| Personal corpus / tutorial / weekly demo | **Personal branch**; never merge wholesale |
| Shared library / CLI / tests / docs for everyone | **Short-lived branch + PR**, or mentor cherry-pick / path-checkout with the same checklist |
| End of stay | **Salvage session**: thin docs/code only → `main`; delete branch |

**Keep:** weekly review as the real quality gate; named personal branches; `main` stays product.

**Add without full PR culture:**

- A short branch contract (no `temp/`, no zip/mp4, no `__pycache__`, no secrets).
- Mentor merges via path-checkout or PR **only** for product files.
- Delete remotes at exit after salvage.

**Introduce PRs** for people touching `semantic_corpus/` core, or as an optional skill in the last month — not as the default for every topic branch.

---

## Related

- [Authorship snapshot (2026-11)](authors_202611.md)
- [Branch consolidation audit (2026-09-29)](branches2026_09_29/README.md)
