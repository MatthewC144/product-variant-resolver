# Image-search result-set resolution v1 — Lite QA review

Date: 2026-10-11. Mode: Lite / Lean Industrial.
Verdict: **PASS — dataset milestone only; aggregation and runtime remain unevaluated**.

Dataset SHA-256:
`7839efc44ced91fe4ae885b7d3019c8d442fcf262fce73470713df52ff8c4e75`.

## Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| ISRS-R1 | Schema represents an ordered list of up to ten result-title pairs. | PASS |
| ISRS-R2 | Membership derives only from 100 positive and 40 no-match development parents. | PASS |
| ISRS-R3 | Casting and complete parent identity are both required and cross-validated. | PASS |
| ISRS-R4 | Every result pairs raw and conservatively cleaned text. | PASS |
| ISRS-R5 | Strict schema rejects extra fields and URLs; final directory contains only `dataset.json`. | PASS |
| ISRS-R6 | Empty result sets are valid; target replacement is rejected. | PASS |
| ISRS-R7 | Collector/checkpoint remained ignored and were deleted after successful validation. | PASS |
| ISRS-R8 | Aggregation, holdout, pricing and runtime work remain zero. | PASS |

## Verification

- Dataset-contract tests: `7 passed`.
- New tracked module: Ruff and strict MyPy PASS.
- Temporary collector: Ruff and strict MyPy PASS.
- The stale stored credential failed before row 1; the owner-supplied credited key was then injected
  into collector process memory only. Two-target smoke returned 10/10 titles before the resumable
  140-target run.
- Final corpus: 140 records, 1,108 ordered title hits, 23 empty result sets, 0 holdout targets.
- Aggregate signal audit: 117/140 result sets contain at least 80% of casting tokens, 60/140 contain
  the toy number, 113/140 contain the release year, and 60/140 contain all three signal classes.

## Finding and next action

The auxiliary dataset represents the predecessor project's ordered evidence shape but does not
change the current resolver boundary or prove that consensus improves identity resolution. If the
experiment continues, the next version should freeze an identity-grouped fit/selection split and
compare top-title, independent-title voting, deterministic evidence fusion and one learned
aggregator on these development records only. Empty result sets must remain explicit provider
failures. Fresh policy holdouts remain sealed.
