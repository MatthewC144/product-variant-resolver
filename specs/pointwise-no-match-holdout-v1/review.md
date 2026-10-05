# Pointwise no-match holdout v1 — QA review

Date: 2026-10-05. Mode: Lite / Lean Industrial. Verdict: **PASS — frozen; NOT SCORED**.

## Requirement evidence

| Requirement | Evidence | Result |
|---|---|---|
| PNMH-R1 | Dataset contains the exact 20 sequential Batch 1 rows and owner-reviewed frozen status. | PASS |
| PNMH-R2 | All 20 normalized brand/casting keys are absent from the bound 1,763-record catalog. | PASS |
| PNMH-R3 | Queries and castings are unique; every row and identity has the exact minimal schema. | PASS |
| PNMH-R4 | Privacy scan finds no URL/collection fields; temporary workspace was removed after verification. | PASS |
| PNMH-R5 | Dataset keeps scoring, model retuning, threshold retuning and runtime activation false. | PASS |
| PNMH-R6 | Authority scope is explicitly third-party-catalog-relative, not manufacturer/global truth. | PASS |

## Finding

The former 0/20 holdout shortfall is now closed at the data-readiness level. Batch 1 supplies 20
independent 2022 query/identity pairs whose exact casting families are absent from the frozen
2023–2026 catalog. This finding does not say the products do not exist; it says they are valid
catalog-relative no-match examples for that exact snapshot.

## Verification

Four focused dataset tests cover immutable hashes, owner scope, exact minimal schemas, uniqueness,
catalog-relative absence and forbidden collection metadata. They pass both before and after removing
the local collection workspace. Scoped Ruff and format checks plus `git diff --check` also pass.

No resolver/model was loaded and no query was scored. No model feature, model parameter, match or
no-match threshold, runtime default or catalog content was changed.

## Next owner gate

The next optional step is one output-blind evaluation of the already frozen Pointwise v2 policy on
this already frozen holdout. It requires a separate explicit authorization. That future run must not
change dataset membership or truth, model/features/thresholds, or runtime behavior in response to
the result.
