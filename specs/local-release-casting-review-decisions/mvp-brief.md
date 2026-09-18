# Local release casting owner decisions — MVP brief

Date: 2026-09-17. Mode: Lite / Lean Industrial. Status: **decision 1 recorded; 4 pending**.

The owner answered question 1 with the verbatim response `` `same_review_family` ``. This authorizes
one review-level relationship decision for the frozen first question only. It does not answer
questions 2–5 and does not authorize release merging, variant selection, color inference, canonical
UUID creation, SQL writes, or Dual RAG changes.

## Requirements

- **LCD-R1 — Packet binding.** WHEN a decision is recorded, THE SYSTEM SHALL validate and bind the
  exact frozen packet SHA, batch ID, question ordinal, and review cluster ID.
- **LCD-R2 — Verbatim owner evidence.** WHEN recording a response, THE SYSTEM SHALL preserve the
  owner's exact text, reviewer identity, UTC timestamp, normalized decision, and narrow interpretation.
- **LCD-R3 — Ordered append-only events.** WHEN decisions accumulate, THE SYSTEM SHALL accept only the
  next unanswered ordinal, retain all prior event bytes/checksums, and reject duplicates or gaps.
- **LCD-R4 — Allowed decisions only.** WHEN an event is created, THE SYSTEM SHALL accept only
  `same_review_family`, `keep_separate`, or `unknown`, and the normalized value SHALL agree with the
  owner's backtick/whitespace-normalized response.
- **LCD-R5 — Bounded effect.** WHEN `same_review_family` is recorded, THE SYSTEM SHALL describe only a
  review-level casting relationship; canonical, variant, color, SQL, evaluation, and runtime effects
  SHALL remain false/zero.
- **LCD-R6 — Deterministic validation.** WHEN a ledger is checked, THE SYSTEM SHALL recompute every
  event checksum, order, packet reference, question reference, status, and cumulative count.
- **LCD-R7 — Private/public split.** The verbatim answer and question identity SHALL remain in a
  gitignored private ledger. Public artifacts SHALL expose only checksums and aggregate progress.
- **LCD-R8 — Honest progress.** After decision 1, THE SYSTEM SHALL report 1/5 recorded, 4/5 pending,
  one `same_review_family`, and zero canonical promotions, reviewed colors, SQL writes, or requests.

## Tasks

- [x] **LCD-T1** Implement generic ordered owner-decision events and ledger validation. _(→LCD-R1–R6)_
- [x] **LCD-T2** Record question 1 verbatim and publish privacy-bounded aggregate progress. _(→LCD-R2,R7–R8)_
- [x] **LCD-T3** Add QA, evidence, decision/log documentation, commit, and stop for question 2. _(→LCD-R1–R8)_

## Acceptance

The private ledger contains exactly one checksum-bound event for question 1 with normalized decision
`same_review_family`; questions 2–5 remain absent/pending. No project truth or runtime state changes.
