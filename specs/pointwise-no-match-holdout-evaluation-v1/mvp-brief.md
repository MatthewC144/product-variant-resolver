# Pointwise no-match holdout evaluation v1 — MVP brief

Date: 2026-10-05. Mode: Lite / Lean Industrial. Status: **complete; not runtime-authorized**.

## Purpose

Execute the project owner's PNMH-G2 authorization exactly once: evaluate the already frozen
Pointwise v2 policy on the already frozen 20-query catalog-relative no-match holdout. Persist only
aggregate metrics. Do not expose row-level query/prediction data, retune any component or activate
runtime behavior.

## Observable requirements

- **PNMHE-R1 — Frozen bindings.** WHEN evaluation starts, THE SYSTEM SHALL verify the approved
  holdout and policy hashes plus the bound calibration, selection, catalog, model manifest and model
  configuration hashes before reading any query.
- **PNMHE-R2 — One output-blind run.** WHEN PNMH-G2 is executed, THE SYSTEM SHALL score exactly 20
  frozen queries once and SHALL refuse a second run after an output artifact exists.
- **PNMHE-R3 — Pre-registered aggregates.** The result SHALL report only no-match, ambiguous and
  matched counts/rates, aggregate reason counts and min/mean/max calibrated confidence. The safety
  gate SHALL require at least 5 no-match decisions and at most 2 incorrect matched decisions.
- **PNMHE-R4 — No row-level persistence.** The tracked result SHALL NOT contain query, record ID,
  expected identity, candidate, confidence or prediction at row level.
- **PNMHE-R5 — No adaptation.** Dataset membership/answers, model, features and both thresholds
  SHALL remain unchanged before and after scoring.
- **PNMHE-R6 — No runtime authority.** Runtime activation and runtime-default changes SHALL remain
  false regardless of the aggregate outcome.
- **PNMHE-R7 — Authority boundary.** Results SHALL be described as relative to the frozen
  third-party catalog, not manufacturer-certified or global truth.

## Design and decision

The evaluator reuses the pinned local Pointwise scorer, frozen five-feature logistic calibration and
frozen two-threshold policy. It loads one scoring context, calculates each decision in memory and
immediately reduces it to counters and confidence summary statistics. No per-row result structure is
returned or written.

The minimum of five explicit no-match decisions comes from the development gate's minimum accepted
count. The maximum of two matched decisions is a 10% false-match ceiling on 20 known no-match rows.
Ambiguous decisions are reported separately because abstention is safer than an incorrect match.
These gates were written before any holdout output was viewed.

## Tasks

- [x] **PNMHE-T1** Freeze PNMH-G2 and all evaluation input hashes. _(→PNMHE-R1)_
- [x] **PNMHE-T2** Implement one-run in-memory scoring and aggregate reduction. _(→PNMHE-R2–R3)_
- [x] **PNMHE-T3** Add fail-closed row-level privacy and no-adaptation validation. _(→PNMHE-R4–R6)_
- [x] **PNMHE-T4** Execute the single authorized run and persist only its aggregate result.
- [x] **PNMHE-T5** Verify the result, publish AI-eval evidence and update decisions/Project Log.

## Acceptance

All frozen hashes must match; exactly 20 decisions must reduce to internally consistent aggregate
counts and rates; no row-level key may appear; model/features/threshold/dataset/runtime flags must
remain false; the run command must refuse execution once the aggregate result exists. Passing this
evaluation is not runtime authorization.
