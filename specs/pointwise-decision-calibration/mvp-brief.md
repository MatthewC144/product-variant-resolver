# Pointwise decision calibration — MVP brief

Date: 2026-10-05. Mode: Lite / Lean Industrial. Status: **complete**.

## Purpose

Map frozen Pointwise ranking logits to exact-release correctness confidence using only the 100-case
development partition. Select a conservative match/ambiguous threshold without reading or rerunning
the 53-case final test and without inventing no-match labels that the positive-only dataset does not
contain.

## Observable requirements

- **PDC-R1 — Development isolation.** WHEN calibration runs, THE SYSTEM SHALL use only the frozen
  100 development IDs and SHALL report `test_cases_scored=0`.
- **PDC-R2 — Nested split.** WHEN the 100 development cases are calibrated, THE SYSTEM SHALL freeze
  a deterministic, disjoint 70-case calibration-fit / 30-case threshold-selection split.
- **PDC-R3 — Exact-release target.** WHEN a row is labeled for calibration, THE SYSTEM SHALL assign
  positive only when Pointwise Top-1 equals that row's source-relative expected release UUID.
- **PDC-R4 — Conservative selection.** WHEN selecting a match threshold, THE SYSTEM SHALL choose the
  highest-coverage threshold with at least five accepted selection rows and at least 90% empirical
  exact-release precision; all lower-confidence candidate-bearing rows SHALL be ambiguous.
- **PDC-R5 — No synthetic no-match truth.** BECAUSE this dataset contains only catalog-present
  identities, THE SYSTEM SHALL set no-match confidence threshold to zero, use no-match only for an
  empty candidate set, and mark the policy not runtime-eligible.
- **PDC-R6 — Aggregate publication.** WHEN artifacts are saved, THE SYSTEM SHALL publish only the
  logistic weights, policy thresholds, hashes and aggregate counts; no query, case ID, prediction or
  row-level label may be persisted.

## Design

The existing frozen 100-case development IDs are hash-sorted with a new versioned salt. The first
70 fit a deterministic five-feature logistic calibrator; the remaining 30 select one confidence
threshold. The Pointwise model, 25-candidate retrieval and stable candidate rendering are unchanged.
The policy disables the legacy positive-logit requirement and raw-logit margin gate because the
calibrator already consumes the Top-1 logit and Top-1/Top-2 margin. `runtime_eligible=false` blocks
this positive-only policy from being used as a complete production decision policy.

## Tasks

- [x] **PDC-T1** Freeze and validate the nested 70/30 development split. _(→PDC-R1, R2)_
- [x] **PDC-T2** Collect Pointwise features and exact-release correctness in memory. _(→PDC-R1, R3)_
- [x] **PDC-T3** Fit logistic calibration and select the conservative match threshold. _(→PDC-R4, R5)_
- [x] **PDC-T4** Materialize hash-bound aggregate artifacts and add integrity/regression tests.
  _(→PDC-R1–R6)_

## Acceptance

The frozen inputs deterministically reproduce the same calibration and policy bytes. Selection
precision meets the predeclared 90% floor with at least five accepted rows, or the run publishes a
shortfall instead of a policy. The final test artifact and 153-row dataset remain unchanged.

## Acceptance evidence

The deterministic 70/30 split produced 48/70 exact-release Top-1 successes in calibration-fit and
21/30 in threshold-selection. The selected threshold `0.641259466766539` accepts 11 selection rows,
of which 10 are correct: 90.91% empirical precision at 36.67% coverage. The remaining 19 rows are
ambiguous and zero rows are classified as no-match. The artifacts reproduce byte-for-byte, report
`test_cases_scored=0`, persist no row-level output and set `runtime_eligible=false`.

Fifty-seven relevant tests, Ruff, strict MyPy, artifact integrity validation and diff validation pass.
The frozen 153-row dataset and final comparison retain SHA-256 values `b0feeff8...e095c` and
`fdf5c81f...9c5a7`; no final-test run was performed during calibration.
