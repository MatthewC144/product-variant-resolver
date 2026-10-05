# Pointwise no-match development readiness — MVP brief

Date: 2026-10-05. Mode: Lite / Lean Industrial. Status: **complete**.

## Purpose

Determine whether the existing human-reviewed real noisy-name corpus contains enough genuine,
catalog-relative no-match evidence for a future Pointwise policy. This stage is read-only: it must
not override the corpus usage contract, score the resolver, fit calibration, select thresholds or
read the frozen final test.

## Observable requirements

- **PNMR-R1 — Frozen inputs.** WHEN readiness runs, THE SYSTEM SHALL bind the tracked
  `human-labeled-real-noisy-v1` bytes and the frozen 1,763-record third-party catalog snapshot by
  SHA-256 and reject drift.
- **PNMR-R2 — Conservative candidate rule.** WHEN a record is counted as a no-match candidate, THE
  SYSTEM SHALL require a non-empty real `initial_name`, `human_label_confidence=confirmed`, non-empty
  normalized brand and casting, and absence of that exact normalized brand/casting family from the
  frozen catalog.
- **PNMR-R3 — Development split preview.** WHEN candidates are ready, THE SYSTEM SHALL freeze a
  deterministic 32-case calibration-fit / 20-case threshold-selection assignment without scoring
  either partition.
- **PNMR-R4 — Existing permission remains authoritative.** IF the human corpus still lists
  `calibration_training` and `threshold_selection` in `excluded_from`, THEN readiness SHALL remain
  blocked behind a separate owner authorization and SHALL NOT write calibration or policy artifacts.
- **PNMR-R5 — Aggregate-only publication.** WHEN readiness is materialized, THE SYSTEM SHALL publish
  counts, hashes, rules, blockers and negative guardrails only; query text, case IDs, labels and
  partition membership SHALL NOT be persisted in the tracked artifact.
- **PNMR-R6 — Evaluation isolation.** WHEN readiness runs, THE SYSTEM SHALL load neither resolver nor
  neural model, SHALL score zero development/final cases and SHALL leave runtime defaults unchanged.

## Design

The audit joins no model output. It normalizes only the human-confirmed expected brand/casting and
the frozen catalog's brand/casting families. Exact family presence excludes a row from the negative
candidate set; exact absence makes it a candidate, not yet authorized calibration truth. Candidate
and prospective split membership are represented publicly only by SHA-256 digests.

The 32/20 split reserves the original benchmark minimum of twenty no-match rows for independent
development threshold selection while retaining thirty-two negatives for a later calibration fit.
This readiness stage does not decide the eventual no-match threshold or make the current neural
policy runtime-eligible.

## Tasks

- [x] **PNMR-T1** Implement strict frozen-input and candidate-set validation. _(→PNMR-R1, R2)_
- [x] **PNMR-T2** Freeze the aggregate-only 32/20 prospective split and readiness manifest.
  _(→PNMR-R3, R5)_
- [x] **PNMR-T3** Enforce permission, model, final-test and runtime negative guardrails.
  _(→PNMR-R4, R6)_
- [x] **PNMR-T4** Add deterministic integrity tests and document the required owner decision.
  _(→PNMR-R1–R6)_

## Acceptance

The same frozen inputs reproduce identical readiness bytes. The manifest reports the exact eligible
candidate count and 32/20 assignment, retains both usage blockers, contains no row-level keys, and
records zero resolver/model/final-test work. No calibration or policy artifact changes in this stage.

## Acceptance evidence

The audit found 91 confirmed records with real query text. Thirty-nine expected brand/casting
families are present in the frozen catalog and are excluded; 52 are absent and form the prospective
negative set. Of those, 46 use the catalog's Hot Wheels brand and six use other brands. All 52 case
IDs, normalized queries and expected families are unique. The public artifact stores only candidate
and split SHA-256 digests, not those row values.

The deterministic prospective split is 32 calibration-fit / 20 threshold-selection. Permission
remains unchanged and blocked for both uses. Sixty relevant tests, Ruff, strict MyPy, CLI
integrity validation and diff validation pass; resolver/model loads, development scoring, final-test
reads and final-test scoring all remain zero.
