# Repository Hygiene Cleanup v1 — Evidence

Date: 2026-10-11  
Verdict: **PASS**

## Baseline

The checkout contained 1,112 tracked files: 247 under `data`, 219 under `docs`, 174 under `specs`,
144 under `tests`, 100 under `src`, 88 under `reports`, 77 under `scripts`, and 28 under
`artifacts`. No `.env`, virtual environment, cache, `HW data`, `model-cache`, or local collection
workspace was tracked.

The size audit found four 43.3 MiB safetensors checkpoints and six historical reports between about
7 and 41 MiB. Exact duplicate content above 100 KiB was limited to tokenizer/vocabulary files shared
by the two independent checkpoint packages. Those packages are checksum-bound and intentionally
self-contained, so no model/report bytes were deleted.

## Organization outcome

The root README now contains a repository map. Thirteen GitHub-facing directory indexes explain:

- active runtime versus offline experiment modules;
- runtime catalogs versus evaluation/governance data;
- current specs versus historical task IDs;
- generated reports versus active configuration;
- trained-but-unselected model artifacts;
- scripts that are safe validators versus owner-gated state transitions;
- optional runtime/database/UI boundaries.

`REAL-CATALOG-ROADMAP.md`, `HUMAN-STORAGE-PROFILE-GUIDE.md`, and
`T49-2-ISOLATED-TEST-PLAN.md` retain stable paths but now state Historical status before their old
content. The current docs index no longer presents the storage guide as architecture.

## Removed ambiguity

- Package metadata now describes confidence-aware product entity resolution and learning-to-rank.
- Public directory indexes state that artifact/config/module presence is not runtime activation.
- README explicitly states that no project-wide open-source license has been selected.
- The obsolete Fandom permission-request template was removed because it was not permission
  evidence. Historical context and Git recovery remain.
- `.gitattributes` makes GitHub treat safetensors as binary and large report/evaluation JSON as
  generated.

## Automated guardrails

Four new hygiene tests verify directory indexes, historical banners, removal of the obsolete draft,
current package wording, GitHub attributes, and absence of local-only tracked paths. The existing
claim/link suite now traverses all new directory indexes.

Verification result: 70 focused tests passed; Ruff passed; strict MyPy passed on the active six-file
runtime scope; current terminology, links, secrets, and diff whitespace checks passed.

## Non-actions

No model, score, threshold, policy, dataset membership, authority record, runtime source, API
response, or frozen metric changed. No holdout or training/evaluation run was opened.
