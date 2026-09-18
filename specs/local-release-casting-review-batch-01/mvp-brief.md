# Local release casting review batch 01 — MVP brief

Date: 2026-09-17. Mode: Lite / Lean Industrial. Status: **complete; awaiting owner answers**.

Owner authorization: 「幫我進行下一步」 authorizes preparation of the bounded owner-review packet
described by the completed casting queue milestone. It does not authorize answering the questions,
canonical promotion, catalog mutation, color inference, SQL writes, or publication of private labels.

## Purpose

Prepare exactly five high-priority casting questions that a non-technical owner can answer. Batch 01
contains the one cross-source exact candidate, the two normalization-collision clusters, and the two
synthetic-fixture-only exact candidates. It freezes evidence before any owner answer is recorded.

## Observable requirements

- **LCB-R1 — Frozen upstream.** WHEN the batch is built, THE SYSTEM SHALL verify the private queue,
  its public checksum, and the source staging bundle before selecting questions.
- **LCB-R2 — Fixed bounded selection.** WHEN batch 01 is built, THE SYSTEM SHALL select exactly the
  five predeclared cluster IDs and SHALL fail if any is absent, duplicated, promoted, or changed.
- **LCB-R3 — Attributable evidence.** WHEN a question is rendered, THE SYSTEM SHALL include the raw
  casting labels, source IDs, toy numbers, years, collector numbers, series, variant-note text, and
  exact candidate summaries required to understand the grouping question.
- **LCB-R4 — Clear decision semantics.** WHEN the owner reviews an item, THE SYSTEM SHALL offer only
  `same_review_family`, `keep_separate`, or `unknown`, and SHALL explain that the first option is a
  review-level relationship rather than release-variant or canonical approval.
- **LCB-R5 — No prefilled answer.** WHILE the owner has not responded, THE SYSTEM SHALL store every
  decision as `null`, mark every item `pending_owner`, and report zero accepted/rejected decisions.
- **LCB-R6 — No attribute inference.** WHEN source model labels contain `2nd Color` or other release
  notes, THE SYSTEM SHALL preserve the literal note but SHALL NOT infer a physical color or variant.
- **LCB-R7 — Deterministic private/public split.** WHEN identical inputs are built, THE SYSTEM SHALL
  reproduce the same packet/checksum. The complete packet SHALL remain gitignored; public artifacts
  SHALL contain only selection-type counts and hashes, without labels, toy numbers, or source rows.
- **LCB-R8 — No downstream mutation.** WHEN the packet is prepared or checked, THE SYSTEM SHALL make
  zero catalog, PostgreSQL, API, evaluation, calibration, and Dual RAG runtime changes.

## Design

```text
validated private casting queue + validated source staging
  -> fixed five-cluster allowlist
  -> private evidence packet + human-readable questions (gitignored)
  -> public aggregate manifest/report (counts and hashes only)
  -> stop and wait for owner decisions
```

The selection is intentionally small. The cross-source item tests how existing review knowledge
should be related; the two collisions test whether normalization hid meaningful differences; the two
fixture-name candidates test whether an observed family name should be related to a synthetic fixture
concept without selecting any of its synthetic variants.

## Tasks

- [x] **LCB-T1** Implement the fixed, deterministic five-question packet builder. _(→LCB-R1–R6)_
- [x] **LCB-T2** Add private/public artifact checks and a CLI. _(→LCB-R7–R8)_
- [x] **LCB-T3** Add tests, QA evidence, decision record, README/roadmap, and Project Log. _(→LCB-R1–R8)_

## Acceptance

Batch 01 contains five pending questions and 18 source observations: one cross-source candidate, two
normalization collisions, and two fixture-only candidates. Recorded decisions, canonical changes,
reviewed colors, SQL writes, and network requests remain zero. The next action is owner review.
