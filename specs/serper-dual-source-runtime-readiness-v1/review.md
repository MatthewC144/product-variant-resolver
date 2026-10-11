# Serper dual-source runtime readiness v1 — QA review

Date: 2026-10-10. Mode: Lite / Lean Industrial.
Verdict: **PASS — readiness audit; runtime remains blocked**.

Readiness artifact SHA-256:
`d19fe5acdc1603eb7e0781c8e757f183c232efba1ad6f43d6d4aace168cc5364`.

## Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| SDSRR-R1 | Dataset, grouped split, development selection and one-shot final hashes/contracts validate. | PASS |
| SDSRR-R2 | v2 calibration/policy and balanced result validate; `runtime_eligible=false`. | PASS |
| SDSRR-R3 | Artifact marks legacy-to-dual-source transfer unvalidated. | PASS |
| SDSRR-R4 | Existing 50-target final is ineligible for fitting, threshold selection or new policy work. | PASS |
| SDSRR-R5 | Missing source-matched negatives/fresh holdout produce a blocked status and concrete next contract. | PASS |
| SDSRR-R6 | Recursive privacy guard rejects row-level fields; tracked artifact is aggregate-only. | PASS |
| SDSRR-R7 | Guardrails record zero network, model, resolver, scoring, calibration, threshold and runtime work. | PASS |
| SDSRR-R8 | `--check` recomputes the artifact and rejects source or output drift. | PASS |

## Verification

- Focused tests: `25 passed` across the new readiness suite and existing dual-source evaluation.
- Ruff: PASS for the new module and tests.
- MyPy strict: PASS for the new module.
- Artifact CLI `--check`: PASS.
- Secret and diff hygiene: PASS.

## Finding

The audit confirms a real distinction: the frozen MiniLM Pointwise ranker has dual-source ranking
evidence, but the decision policy does not have source-matched calibration or fresh policy-test
evidence. The existing v2 policy was built on older image-search positives plus human no-match data,
abstains on 73.97% of its balanced evaluation, and remains runtime-ineligible.

The smallest next data contract reuses the existing 100 positive development identities and
collects 80 new identities (160 paired observations): 40 catalog-relative no-match development,
20 fresh catalog-present holdout and 20 fresh catalog-relative no-match holdout. The existing
50-target ranking final remains excluded from all new policy work.

## Next permitted action

Collect and freeze the minimal dual-source policy dataset. Temporary collection code, API secrets
and images remain untracked; only the minimized final dataset may enter Git. No calibration,
threshold selection, policy evaluation or runtime activation is authorized by this audit.
