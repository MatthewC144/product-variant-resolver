# Family Retrieval Evaluation — Requirements

> Mode: Lite / Lean Industrial
>
> Phase: Build
>
> Status: Confirmed; T48.1–T48.3 complete
>
> Proposed benchmark: `family-retrieval-holdout-v1`

## Purpose

Measure whether Human Knowledge RAG v2 can retrieve accepted casting families from separately
written noisy queries without reusing its indexed names as the test questions, changing the frozen
retriever after seeing test results, or allowing evaluation labels to become canonical or
PostgreSQL data.

## Functional requirements

### FRE-R1 — Frozen system under test

WHEN the evaluation source pack is created, THE SYSTEM SHALL freeze the Human Knowledge index
version, human-catalog version/checksum, review-family projection version/checksum, normalization
rules, dense dimensions, RRF constant, and candidate limit before any scored retrieval is run.

### FRE-R2 — Output-blind independent query authoring

WHEN a challenge query is authored, THE SYSTEM SHALL record its author, method, case type, noise
tags, and a declaration that no retriever candidates/ranks/scores were viewed; query text SHALL NOT
be copied from the indexed searchable text, the 2025 Fandom staging labels, or existing human-label
queries.

### FRE-R3 — Exact benchmark composition

WHEN the proposed query pack is complete, THE SYSTEM SHALL contain exactly 105 cases: 84 positive
family cases, 4 accepted-merge controls, 7 held-family controls, and 10 unrelated/no-overlap
controls; it SHALL reject duplicate case IDs or query strings.

### FRE-R4 — Complete positive-family coverage

WHEN positive cases are validated, THE SYSTEM SHALL represent each of the 42 accepted review
families exactly twice under one casting-family group: once as `marketplace_noise` and once as
`lexical_variation`.

### FRE-R5 — Non-trivial query rules

WHEN a positive query is accepted, THE SYSTEM SHALL reject normalized text equal to a document's
brand/casting or alias string; each `lexical_variation` query SHALL break the full normalized
casting phrase and document at least one abbreviation, misspelling, spacing, punctuation, or seller-
wrapper challenge, including all four single-token families.

### FRE-R6 — Safety-control coverage

WHEN control cases are validated, THE SYSTEM SHALL cover all 4 accepted merge families as existing
provisional-variant casting controls, all 7 held families as forbidden review-family identities,
and 10 unrelated queries whose normalized tokens do not overlap any human-knowledge document.

### FRE-R7 — Attributable human label approval

WHEN labels become scoring-eligible, THE SYSTEM SHALL require a separate project-owner decision
file covering every query exactly once with reviewer, timestamp, decision, expected identity/type
or explicit negative expectation, and reason; pending, partial, changed, or duplicate approval
SHALL fail closed.

### FRE-R8 — Deterministic benchmark and manifest

WHEN the query pack and owner decisions are accepted, THE SYSTEM SHALL produce a deterministic
benchmark and manifest that freeze all input/output checksums, exact class/style/group counts,
system-under-test versions, authorship declarations, test-only usage, and excluded uses.

### FRE-R9 — Casting-grouped test isolation

WHEN the benchmark is scored, THE SYSTEM SHALL assign every case to the fixed `test` split, keep
related cases under one casting-family group, declare zero train/dev cases, and prohibit fitting,
threshold selection, query rewriting, or retriever changes using its labels or results.

### FRE-R10 — Read-only evaluator

WHEN evaluation runs, THE SYSTEM SHALL load the frozen benchmark and existing
`human-knowledge-hybrid-v2` retriever read-only, access expected labels only after retrieval, and
SHALL NOT modify the index, runtime configuration, canonical catalog, calibration/policy,
PostgreSQL, or benchmark files.

### FRE-R11 — Traceable metrics and errors

WHEN scoring completes, THE SYSTEM SHALL report raw per-case candidate IDs/types/ranks, aggregate
positive Recall@1/5 and MRR@5, family coverage@5, metrics by challenge style, merge-control
Recall@5, forbidden-family hits, unrelated-query non-empty results, and categorized failures.

### FRE-R12 — Precommitted quality gate

WHEN the frozen v1 report is judged, THE SYSTEM SHALL require positive Recall@5 `>=0.85`, Recall@1
`>=0.65`, MRR@5 `>=0.75`, both positive challenge styles Recall@5 `>=0.75`, family coverage@5
`>=0.90`, merge-control Recall@5 `=1.0`, forbidden-family hits `=0`, and unrelated non-empty results
`=0` for a PASS.

### FRE-R13 — Honest failure and no test-set tuning

IF any quality or safety gate fails, THEN THE SYSTEM SHALL publish FAIL with failed cases and error
categories, keep the family source debug-only, and SHALL NOT tune or select a replacement model on
`family-retrieval-holdout-v1`; a changed retriever SHALL require a new versioned holdout for final
evaluation.

### FRE-R14 — Versioned report and AI-eval record

WHEN evaluation completes, THE SYSTEM SHALL write versioned JSON and Markdown reports containing
dataset/model/checksum metadata, raw counts, formulas, gates, pass/fail, limitations, and a linked
AI-eval rubric record; it SHALL NOT claim production accuracy from this bounded synthetic challenge.

### FRE-R15 — Identity, persistence, and privacy boundary

WHILE T48 is active, THE SYSTEM SHALL keep all benchmark identities outside canonical responses,
catalog promotion, calibration, threshold selection, release-variant truth, PostgreSQL ingestion,
and the approximately 3,000-row expansion; reports SHALL avoid raw private user data and secrets.

### FRE-R16 — Reproducibility and regression gate

WHEN T48 is verified, THE SYSTEM SHALL reproduce the benchmark/report from frozen inputs, pass
positive/negative evaluator tests and the complete existing suite/data chain, preserve frozen
canonical metrics and T47 behavior, and document the next decision without modifying files outside
the Product Variant Resolver repository.

## Acceptance boundary

A PASS permits the current family retriever to remain a measured debug/review suggestion source and
allows T49 to design PostgreSQL scale experiments. It does not authorize canonical matching,
release-variant correctness, production deployment, or 3,000-row ingestion. A FAIL is a useful
result: it identifies the retrieval weaknesses that must be redesigned before persistence work.

## Out of scope

- Training, tuning, or replacing retrieval models with the v1 holdout.
- Reusing the 42 exact indexed family names as scored queries.
- Treating staging rows, family decisions, or projections as evaluation ground truth without the
  separate T48 owner-approval layer.
- Canonical catalog/calibration/policy changes.
- PostgreSQL/pgvector implementation or latency claims.
- New yearly-list ingestion or release-variant materialization.
