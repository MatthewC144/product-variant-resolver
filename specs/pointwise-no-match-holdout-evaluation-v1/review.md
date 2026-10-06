# Pointwise no-match holdout evaluation v1 — QA review

Date: 2026-10-05. Mode: Lite / Lean Industrial. Verdict: **PASS — aggregate gate; NOT RUNTIME AUTHORIZED**.

## Requirement evidence

| Requirement | Evidence | Result |
|---|---|---|
| PNMHE-R1 | Dataset, catalog, calibration, policy, selection, model config and model manifest hashes match PNMH-G2. | PASS |
| PNMHE-R2 | Exactly 20 rows were scored in the one authorized run; a second run is refused when results exist. | PASS |
| PNMHE-R3 | Result contains 11 no-match, 9 ambiguous and 0 matched; both pre-registered gates pass. | PASS |
| PNMHE-R4 | Artifact contains aggregate counters/statistics only and recursively rejects row-level keys. | PASS |
| PNMHE-R5 | Dataset/answers/model/features/thresholds remained unchanged. | PASS |
| PNMHE-R6 | Runtime authorization/default flags remain false. | PASS |
| PNMHE-R7 | Result states frozen third-party-catalog-relative authority only. | PASS |

## Result

The frozen policy explicitly rejected 11/20 queries, giving catalog-relative no-match recall of
55%. It abstained on 9/20 and incorrectly matched 0/20, so the false-match rate is 0%. The
pre-registered minimum was five no-match decisions and the maximum was two matched decisions; both
conditions pass.

All nine undecided records remained between the existing no-match and match thresholds. Their
existence is not hidden or reclassified: the policy preferred `ambiguous` over an unsupported match.
No row-level analysis was persisted, so this holdout cannot now become tuning data.

## Verification

The tracked aggregate result SHA-256 is
`937eabc88164532ce686d5c1d4521d0ffef58efc2691d8836cba723fd68b05c6`. Focused tests validate the
hash, bindings, aggregate arithmetic, gates, privacy guard, non-runtime flags and one-run refusal.
The module passes scoped Ruff, strict MyPy and compile checks.

## Limitation and next gate

This is a 20-row negative-only holdout. It tests rejection behavior but cannot measure catalog-present
exact-match accuracy or false no-match rate on positives, and it is not a manufacturer/global-truth
benchmark. The PASS therefore supports the frozen policy's bounded rejection behavior only. Any
runtime proposal still requires owner review and balanced untouched evidence; this result cannot be
used to change the model, features or thresholds.
