# Pointwise three-class development calibration — MVP brief

Date: 2026-10-05. Mode: Lite / Lean Industrial. Status: **complete**.

## Purpose

Use the PNMR-G1-authorized 52 real catalog-relative no-match cases together with the frozen 100
catalog-present development cases to fit and select a three-state Pointwise decision policy. This is
development evidence only: final-test retuning and runtime activation remain prohibited.

## Observable requirements

- **PTCDC-R1 — Governed inputs.** WHEN calibration starts, THE SYSTEM SHALL validate the PNMR-G1
  owner authorization and overlay, the frozen 52-row candidate set, 32/20 negative split, 70/30
  positive split, 1,763-row catalog and pinned Pointwise model before scoring.
- **PTCDC-R2 — Combined fit.** WHEN fitting calibration, THE SYSTEM SHALL use exactly 70
  catalog-present and 32 catalog-relative no-match rows, assigning a positive target only when a
  catalog-present row's Pointwise Top-1 equals its expected release UUID.
- **PTCDC-R3 — Independent selection.** WHEN choosing thresholds, THE SYSTEM SHALL use exactly 30
  catalog-present and 20 no-match rows that were excluded from fitting.
- **PTCDC-R4 — Match gate.** WHEN selecting `match_threshold`, THE SYSTEM SHALL choose the
  highest-coverage threshold with at least five matched decisions and at least 90% exact-release
  precision.
- **PTCDC-R5 — No-match gate.** WHEN selecting `no_match_threshold`, THE SYSTEM SHALL require at
  least five no-match decisions, at least 90% no-match precision and at most 10% false-no-match rate
  among catalog-present selection rows; among eligible thresholds it SHALL maximize no-match recall
  with conservative deterministic tie-breaking.
- **PTCDC-R6 — Shortfall behavior.** IF either decision gate cannot be met, THEN THE SYSTEM SHALL
  publish an aggregate shortfall instead of a policy and SHALL NOT relax the frozen gates.
- **PTCDC-R7 — Aggregate-only output.** WHEN artifacts are saved, THE SYSTEM SHALL persist only
  calibration weights, thresholds, parent hashes, aggregate counts and metrics; it SHALL NOT persist
  query text, case IDs, row labels, predictions or split membership.
- **PTCDC-R8 — Runtime/final isolation.** WHEN development calibration completes, THE SYSTEM SHALL
  report zero final-test reads/scores, leave runtime defaults unchanged and set any resulting policy
  to `runtime_eligible=false`.

## Design

The five frozen ranking features remain unchanged. A new logistic artifact is fit on 102 rows: 70
catalog-present positives/incorrect-top1 examples plus 32 governed no-match negatives. Thresholds
are selected only on the disjoint 50-row selection partition. High confidence may become matched,
low confidence may become no-match only if PTCDC-R5 passes, and the interval between thresholds is
ambiguous.

The no-match threshold candidates are deterministic floating-point successors of observed
selection confidences, matching the policy's strict `< no_match_threshold` behavior. If several
thresholds achieve the same no-match recall, fewer catalog-present errors, higher precision and a
lower threshold win in that order.

## Tasks

- [x] **PTCDC-T1** Reuse one pinned Pointwise scoring context for both governed input sets.
  _(→PTCDC-R1–R3)_
- [x] **PTCDC-T2** Fit the combined logistic artifact and implement both frozen threshold gates.
  _(→PTCDC-R2–R6)_
- [x] **PTCDC-T3** Materialize aggregate-only versioned artifacts with strict parent validation.
  _(→PTCDC-R1, R7, R8)_
- [x] **PTCDC-T4** Add unit, integrity, API fail-closed and regression validation.
  _(→PTCDC-R1–R8)_
- [x] **PTCDC-T5** Record metrics, limitations and the next permitted action in QA and Project Log.
  _(→PTCDC-R6–R8)_

## Acceptance

The same local frozen inputs deterministically reproduce the same calibration, optional policy and
selection bytes. A policy exists only if both gates pass. All artifacts remain aggregate-only,
final-test counts remain zero, and the service refuses the development-only policy at runtime.

## Acceptance evidence

Both gates passed without relaxation. On the 50-row threshold-selection partition, the match
threshold `0.9424986749501544` accepts 7 rows and all 7 are exact-release correct (100% precision,
14% total selection coverage). The no-match threshold `0.15503728534608827` predicts 10 rows, 9 of
which are catalog-relative no-match (90% precision, 45% no-match recall); one of 30 catalog-present
rows is falsely rejected (3.33%, below the 10% limit). The remaining 33 rows are ambiguous.

Calibration and policy reproduce byte-for-byte from all 152 development rows. Sixty-seven relevant
tests, Ruff, strict MyPy, v1/v2 CLI integrity checks and diff validation pass. No row-level output is
persisted, final-test reads/scores remain zero, and the v2 policy is explicitly
`runtime_eligible=false`.
