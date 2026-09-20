# Human Knowledge false-positive development — MVP brief

Date: 2026-09-20. Mode: Lite / Lean Industrial. Status: **implemented and baseline verified**.

## Purpose and boundary

Create a new development-only benchmark that exposes same-make and related-model false-positive
behavior without reading, changing, or rerunning the private 20-case local-family evaluation. This
step records the current v4 baseline only; it does not implement or select a mitigation and does not
change the API or Dual RAG runtime.

## Requirements

- **HKFP-R1 — Separate public source.** WHEN the pack is built, THE SYSTEM SHALL use only the
  committed 142-document Human Knowledge corpus and SHALL NOT load local private projection,
  benchmark, raw result, or labels.
- **HKFP-R2 — Development-only cases.** The pack SHALL contain exactly 24 manually specified dev
  cases. Each case SHALL name one required and one distinct forbidden knowledge document already
  present in the 142-document corpus.
- **HKFP-R3 — Confusable relationship.** Required and forbidden identities SHALL share at least one
  normalized identity-core token while remaining distinct knowledge IDs and UUIDs.
- **HKFP-R4 — Non-exact query.** Every query SHALL include contextual wording and SHALL not equal
  either required or forbidden casting/alias after normalization.
- **HKFP-R5 — Frozen inputs.** Pack, manifest, source corpus hashes, query order, expected IDs, and
  fixed v4 baseline configuration SHALL be deterministic and byte-checkable before retrieval.
- **HKFP-R6 — Honest baseline.** Evaluation SHALL run the selected v4 retriever at Top 5 over exactly
  142 documents and SHALL publish required Recall@5, forbidden-hit cases/count, safety accuracy,
  errors, and per-case ranks without a PASS claim.
- **HKFP-R7 — No selection.** This feature SHALL NOT introduce an admission threshold, choose a
  winner, tune a retriever, or evaluate the private local-family test set.
- **HKFP-R8 — No runtime mutation.** Runtime configuration, API behavior, canonical catalog,
  PostgreSQL, existing development/final evidence, and local five-document status SHALL remain
  unchanged.
- **HKFP-R9 — Safe publication.** First build/evaluation SHALL create immutable artifacts; exact
  rerun SHALL validate and return `unchanged`; partial, stale, or conflicting outputs SHALL fail.

## Design

`human_knowledge_false_positive_development.py` owns a hand-authored 24-case map and resolves its
IDs against the committed catalog without invoking retrieval. `--freeze-pack` writes a deterministic
pack and manifest. The default command validates those frozen inputs, runs the current
`human-knowledge-hybrid-v4` configuration (`floor=0.5`, `weight=1.0`, `hashing-v1/192`), and writes
public raw ranks plus an aggregate report. `--check` reconstructs metadata and scoring without
retrieval.

The required target proves that filtering cannot simply remove every ambiguous query. The forbidden
target measures over-admission among intentionally related identities. Because every case is dev,
future mitigation may use these results; the private 20-case evaluation remains untouched and is not
eligible for tuning.

## Tasks

- [x] **HKFP-T1** Implement deterministic pack construction and corpus-bound validation. _(→R1–R5)_
- [x] **HKFP-T2** Implement baseline collection, deterministic scoring, publication, and check mode.
  _(→R5–R9)_
- [x] **HKFP-T3** Add contract, privacy-boundary, scoring, tamper, and idempotency tests. _(→R1–R9)_
- [x] **HKFP-T4** Freeze the real pack, record baseline, run QA, and update evidence, decisions,
  README, roadmap, and project log. _(→R1–R9)_

## Acceptance

A deterministic 24-case development pack and baseline report now exist using only the current public
142-document corpus. Required Recall@5 is 24/24, while 18/24 cases also admit their forbidden
candidate, yielding safety accuracy@5 of 0.25. No mitigation is selected, and the immutable private
evaluation and runtime remain untouched.
