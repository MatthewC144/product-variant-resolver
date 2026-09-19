# Local release casting review-family materialization — MVP brief

Date: 2026-09-18. Mode: Lite / Lean Industrial. Status: **implemented and verified**.

## Purpose and scope

Convert the complete five-question local casting owner-decision ledger into a deterministic,
private review-layer relationship registry. The registry makes the decisions machine-readable
without turning them into canonical products, release variants, colors, database rows, evaluation
labels, or Dual RAG documents.

The earlier `data/review_family_registry.json` belongs to a separate 2025 Wiki adjudication dataset.
This feature therefore uses a distinct schema, version, CLI, private directory, and public aggregate
report for the owner-supplied 2023–2026 release staging lineage.

## Requirements

- **LRFM-R1 — Complete authority.** WHEN materialization starts, THE SYSTEM SHALL verify the frozen
  packet and complete checksum-bound decision ledger, and SHALL reject an incomplete or stale ledger.
- **LRFM-R2 — Exact relationship scope.** WHEN an event is `same_review_family`, THE SYSTEM SHALL
  create one deterministic review relationship bound to its question, cluster, event hash, labels,
  normalized key, and source references.
- **LRFM-R3 — Non-affirmative decisions.** IF an event is `keep_separate` or `unknown`, THEN THE
  SYSTEM SHALL preserve it as an exclusion and SHALL NOT create a relationship.
- **LRFM-R4 — Release hold.** WHEN a source observation is referenced, THE SYSTEM SHALL keep it as a
  distinct `held_for_variant_review` reference and SHALL reject duplicate source assignments.
- **LRFM-R5 — Candidate boundary.** WHEN a question contains candidate evidence, THE SYSTEM SHALL
  record only its checksum and `context_only_not_selected` status; no candidate product or family
  identity SHALL be selected.
- **LRFM-R6 — No downstream promotion.** WHILE this feature is review-layer-only, canonical UUIDs,
  reviewed colors, PostgreSQL writes, evaluation labels, runtime indexing, and Dual RAG changes
  SHALL remain null/zero/false.
- **LRFM-R7 — Deterministic integrity.** WHEN the same packet and ledger are rebuilt, THE SYSTEM
  SHALL produce identical relationship IDs, item hashes, registry checksum, manifest, and report.
- **LRFM-R8 — Idempotent publication.** WHEN exact outputs already exist, THE SYSTEM SHALL return
  `unchanged`; IF only part exists or any byte conflicts, THEN it SHALL fail without overwriting.
- **LRFM-R9 — Rollback boundary.** IF first-time publication fails after creating an output
  directory, THEN THE SYSTEM SHALL remove only directories created by that attempt.
- **LRFM-R10 — Private/public split.** The complete registry SHALL remain gitignored. Public output
  SHALL contain only schema/version, input and registry hashes, aggregate counts, and zero-effect
  boundaries—no labels, cluster IDs, source IDs, toy numbers, or verbatim answers.
- **LRFM-R11 — Honest batch result.** For the current complete ledger, THE SYSTEM SHALL report five
  materialized review relationships, 18 held source references, zero exclusions, and zero canonical,
  color, SQL, evaluation, network, or runtime effects.

## Design

`release_casting_review_materialization.py` reads only artifacts already validated by
`check_batch` and `check_decisions`. Each affirmative event becomes a relationship whose ID is a
stable SHA-256-derived identifier over packet SHA and review cluster—not a UUID and not a canonical
identity. Source observations are copied as private references with explicit variant hold and null
canonical/color fields. Candidate evidence is represented only by its digest.

The private output is `registry.json` under the gitignored local data tree. The committed public
directory contains `manifest.json` and `report.md`. First publication preflights both directories,
writes them as a pair, and rolls back newly created directories on failure. Existing exact pairs are
read-only/idempotent; partial or stale pairs fail closed.

## Tasks

- [x] **LRFM-T1** Implement deterministic registry, exclusion, summary, and validators. _(→R1–R7,R11)_
- [x] **LRFM-T2** Implement safe create/unchanged/check publication and privacy-bounded output. _(→R8–R10)_
- [x] **LRFM-T3** Add unit, integration, tamper, privacy, idempotency, and rollback tests. _(→R1–R11)_
- [x] **LRFM-T4** Generate artifacts, run complete QA, and update evidence/decisions/project log. _(→R1–R11)_

## Acceptance

The current ledger deterministically creates five private review relationships covering 18 unique,
held release references. Re-running is byte-identical and reports `unchanged`; tampering, partial
outputs, duplicate references, incomplete decisions, or widened effects fail closed. Public files
contain aggregates and hashes only. Existing canonical catalog, PostgreSQL, evaluation, API, and
Dual RAG behavior are unchanged.
