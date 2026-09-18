# Local release casting owner decisions — MVP brief

Date: 2026-09-17. Mode: Lite / Lean Industrial. Status: **decisions 1–3 recorded; 2 pending**.

The owner answered question 1 with the verbatim response `` `same_review_family` ``. This authorizes
one review-level relationship decision for the frozen first question only. It does not answer
questions 2–5 and does not authorize release merging, variant selection, color inference, canonical
UUID creation, SQL writes, or Dual RAG changes.

The owner then answered question 2 with the verbatim response ``2. `same_review_family` ``. The
numeric prefix is treated as an explicit question reference: it must equal the event ordinal before
the decision value is normalized. This authorizes the same narrow review-level relationship for
question 2 only; questions 3–5 remain unanswered.

The owner answered question 3 with the verbatim response `same_review_family`. Because it has no
explicit prefix, the append-only sequence supplies the question binding: only ordinal 3 is accepted
after two valid events. This authorizes one more review-level relationship and leaves questions 4–5
unanswered.

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
- **LCD-R9 — Explicit ordinal safety.** WHEN an owner response starts with `<number>.`, THE SYSTEM
  SHALL accept it only when that number matches the recorded question ordinal, preserve the complete
  response verbatim, and reject a mismatched prefix before writing an event.
- **LCD-R10 — Honest cumulative progress.** After decision 2, THE SYSTEM SHALL report 2/5 recorded,
  3/5 pending, two `same_review_family` decisions, and zero canonical promotions, reviewed colors,
  SQL writes, requests, or runtime changes.
- **LCD-R11 — Ordered unprefixed response.** WHEN an unprefixed response is appended after two valid
  events, THE SYSTEM SHALL bind it only to question 3, retain events 1–2 exactly, and reject an
  attempt to skip to another ordinal.
- **LCD-R12 — Third-decision progress.** After decision 3, THE SYSTEM SHALL report 3/5 recorded, 2/5
  pending, three `same_review_family` decisions, and zero canonical promotions, reviewed colors,
  SQL writes, requests, or runtime changes.

## Tasks

- [x] **LCD-T1** Implement generic ordered owner-decision events and ledger validation. _(→LCD-R1–R6)_
- [x] **LCD-T2** Record question 1 verbatim and publish privacy-bounded aggregate progress. _(→LCD-R2,R7–R8)_
- [x] **LCD-T3** Add QA, evidence, decision/log documentation, commit, and stop for question 2. _(→LCD-R1–R8)_
- [x] **LCD-T4** Validate the optional ordinal prefix and record question 2 without rewriting event 1. _(→LCD-R2–R7,R9)_
- [x] **LCD-T5** Refresh aggregate evidence, QA, decision/log documentation, and stop for question 3. _(→LCD-R1–R10)_
- [x] **LCD-T6** Record the unprefixed question 3 response through the existing ordered contract. _(→LCD-R1–R7,R11)_
- [x] **LCD-T7** Refresh aggregate evidence, QA, decision/log documentation, and stop for question 4. _(→LCD-R1–R12)_

## Acceptance

The private ledger contains exactly three ordered, checksum-bound events for questions 1–3, all with
normalized decision `same_review_family`. The second response retains its matching `2.` prefix, the
third remains unprefixed, and events 1–2 remain byte-for-byte unchanged. Questions 4–5 remain
absent/pending. No project truth or runtime state changes.
