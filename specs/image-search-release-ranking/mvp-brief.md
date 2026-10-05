# Image-search release ranking — MVP brief

Date: 2026-10-05. Mode: Lite / Lean Industrial. Status: **in progress**.

## Purpose

Improve exact-release ranking for the frozen 153-row image-search benchmark without tuning on the
final test set. First freeze a deterministic 100-case development / 53-case test split; subsequent
ranking and calibration work may read development metrics only until an explicit final evaluation.

## Observable requirements

- **ISRR-R1 — Dataset-bound split.** WHEN a split is requested, THE SYSTEM SHALL require the exact
  frozen dataset SHA-256 and 153-row schema; changed bytes or row counts fail closed.
- **ISRR-R2 — Deterministic partition.** WHEN the same dataset, salt and algorithm are used, THE
  SYSTEM SHALL return the same 100 development and 53 test IDs plus assignment SHA-256.
- **ISRR-R3 — No overlap.** WHEN the split is built, development and test SHALL be disjoint and
  their union SHALL contain every dataset case exactly once.
- **ISRR-R4 — Minimal dataset.** WHEN the split is frozen, THE SYSTEM SHALL NOT add split fields or
  another row-level artifact to the final dataset directory.
- **ISRR-R5 — Test isolation.** WHILE ranking/calibration is under development, default evaluation
  SHALL score development only; test evaluation requires an explicit CLI selection.
- **ISRR-R6 — Honest baseline.** WHEN the development baseline is recorded, THE SYSTEM SHALL note
  that only aggregate full-dataset metrics had been observed before the split and no row-level
  predictions/failures were consulted.

## Design

The tracked dataset bytes are pinned by SHA-256. Each case receives a SHA-256 key derived from a
versioned salt, case ID and normalized expected casting. Sorting by this key and taking the first
100 freezes development; the remaining 53 freeze test. The assignment itself is represented by a
canonical aggregate checksum in code/report metadata, not by a second data file.

## Tasks

- [x] **ISRR-T1** Implement and verify the frozen 100/53 deterministic split. _(→ISRR-R1–R4)_
- [x] **ISRR-T2** Run and record development-only baseline metrics. _(→ISRR-R5–R6)_
- [ ] **ISRR-T3** Develop release-aware pointwise and listwise ranking candidates using development
  only. Final test remains closed. _(future; →ISRR-R5)_
- [ ] **ISRR-T4** Select on development, then run one explicit final test and document tradeoffs.
  _(future; →ISRR-R5–R6)_

## Acceptance for this step

The exact dataset produces 100 development and 53 test cases, zero overlap, stable assignment hash,
and a development-only aggregate baseline. `dataset.json` remains byte-for-byte unchanged and is
still the only file in its data directory.
