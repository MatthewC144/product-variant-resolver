# Pointwise balanced holdout evaluation v1 — MVP brief

Date: 2026-10-05. Mode: Lite / Lean Industrial. Status: **complete; runtime held**.

## Purpose

Execute PBHE-G1 exactly once: apply the frozen Pointwise v2 decision policy to the frozen 53-case
catalog-present test split, then combine its aggregate metrics with the already frozen 20-case
catalog-relative no-match result. Do not rerun the negative holdout, persist row-level outputs,
retune any component or activate runtime behavior.

## Observable requirements

- **PBHE-R1 — Frozen bindings.** WHEN evaluation starts, THE SYSTEM SHALL verify the approved
  positive dataset, split and policy plus the catalog, calibration, selection, model configuration,
  model manifest, prior ranking comparison and frozen negative result hashes.
- **PBHE-R2 — Honest prior-use scope.** The protocol SHALL state that the 53 positives were
  previously used for ranker evaluation but were not used by Pointwise v2 calibration/threshold
  selection and have no prior v2 policy decisions.
- **PBHE-R3 — One positive run.** THE SYSTEM SHALL score exactly the 53 test rows once and SHALL
  refuse a second positive run after the aggregate output exists. It SHALL reuse, not rescore, the
  20-case negative result.
- **PBHE-R4 — Two identity levels.** Positive aggregates SHALL report casting-level and exact-release
  matched precision/recall separately; casting correctness SHALL NOT substitute for exact-release
  correctness.
- **PBHE-R5 — Pre-registered gates.** At least five exact-release-correct matched decisions, at least
  90% exact precision among matched decisions and at most 10% false no-match on positives are
  required. The frozen negative aggregate gate SHALL also remain passed.
- **PBHE-R6 — Aggregate-only privacy.** No query, case ID, expected identity, candidate, confidence
  or prediction SHALL be persisted per row.
- **PBHE-R7 — No adaptation/runtime.** Dataset/answers/model/features/thresholds and runtime defaults
  SHALL remain unchanged; runtime activation SHALL remain unauthorized regardless of result.

## Design and decision

The positive evaluator reconstructs only the frozen 53-case test membership, binds each expected
release to its evaluation UUID, runs the existing local Pointwise scorer and v2 calibration/policy,
and reduces all row outcomes in memory. It records matched/ambiguous/false-no-match counts,
casting/exact identity metrics, aggregate reasons and confidence summary statistics.

The combined report contains both truth classes but does not claim equal class balance: there are 53
catalog-present positives and 20 catalog-relative negatives. It reports end-to-end exact accuracy,
decisive exact precision, balanced identity recall and abstention, while retaining the class-specific
metrics needed to interpret that unequal composition.

## Tasks

- [x] **PBHE-T1** Freeze PBHE-G1, prior-use disclosure, inputs and gates. _(→PBHE-R1–R2, R5)_
- [x] **PBHE-T2** Implement one-run positive scoring and two-level aggregate reduction. _(→PBHE-R3–R4)_
- [x] **PBHE-T3** Reuse the negative aggregate and create the combined report. _(→PBHE-R3, R5)_
- [x] **PBHE-T4** Add fail-closed privacy, integrity, arithmetic and no-runtime validation. _(→PBHE-R1–R7)_
- [x] **PBHE-T5** Execute the single positive run and persist aggregate results only.
- [x] **PBHE-T6** Complete QA, AI-eval evidence, decision record and Project Log.

## Acceptance

All frozen bindings must match before and after scoring; exactly 53 positive decisions and the frozen
20 negative aggregates must compose 73 cases; gates and rates must be internally reproducible; no
row-level key may appear; the run command must refuse execution once results exist; no model,
threshold, data truth or runtime setting may change. PASS is evidence only, not runtime authority.
