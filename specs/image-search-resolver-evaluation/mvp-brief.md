# Image-search resolver evaluation — MVP brief

Date: 2026-10-05. Mode: Lite / Lean Industrial. Status: **complete**.

Owner authorization: the owner requested that 150–200 image-search queries be sampled from the
local 1,763-row release source, retain casting and full release answers, and then continued to the
next necessary project step. This authorizes a source-relative, local-only evaluation projection.
It does not promote the release source to canonical authority, publish the 1,763 rows, modify the
production catalog, or authorize new network collection.

## Purpose

Evaluate the real resolver against the 153-row `image-search-resolver-v1` dataset while using all
1,763 local releases as the candidate corpus. The runner must distinguish casting-level ranking,
exact release ranking, and final resolver decisions. It must fail closed when the benchmark answer
does not map to exactly one source toy number.

## Observable requirements

- **ISR-R1 — Strict benchmark.** WHEN the dataset is loaded, THE SYSTEM SHALL reject extra fields,
  malformed IDs, duplicate queries/castings, non-contiguous IDs, or casting/identity disagreement.
- **ISR-R2 — Exact source binding.** WHEN readiness is checked, EACH benchmark answer SHALL map by
  toy number to exactly one of the 1,763 source rows and all release fields SHALL agree.
- **ISR-R3 — Local-only projection.** WHEN the candidate catalog is built, THE SYSTEM SHALL create
  deterministic evaluation surrogate IDs in memory and SHALL NOT write or modify canonical data.
- **ISR-R4 — Dual granularity.** WHEN evaluation runs, THE SYSTEM SHALL report casting Top-1 and
  exact-release Top-1 separately, plus exact-release Recall@10 and Recall@25.
- **ISR-R5 — Decision honesty.** WHEN final resolver responses are scored, THE SYSTEM SHALL report
  matched/ambiguous/no-match counts, exact decision accuracy and abstention rate separately from
  ranking metrics.
- **ISR-R6 — Privacy boundary.** WHEN results are emitted, THE SYSTEM SHALL publish aggregate
  counts/metrics only; the 1,763 source rows, row-level outputs and source metadata remain local.
- **ISR-R7 — Authority disclaimer.** WHEN a report is emitted, THE SYSTEM SHALL state that expected
  identities are third-party-source-relative and not manufacturer/global canonical truth.

## Design

```text
tracked 153-row dataset + ignored 1,763-row normalized snapshot
  -> strict schema and exact toy-number/release-field binding
  -> deterministic in-memory CatalogProduct projection
  -> existing signal extraction + sparse/dense/structured retrieval + resolver policy
  -> aggregate-only report to stdout (no default output file)
```

The evaluator reuses the production retrieval and decision code. UUIDv5 values are evaluation
surrogates derived from source record IDs, never canonical authority. The source snapshot's
`staging_only_not_evaluation_or_canonical` marker remains unchanged; this runner is a separately
authorized, read-only projection and labels that boundary in its report.

## Tasks

- [x] **ISR-T1** Implement strict dataset/source validation and deterministic in-memory projection.
  _(→ISR-R1–R3,R6–R7)_
- [x] **ISR-T2** Implement aggregate ranking and resolver-decision metrics with a CLI.
  _(→ISR-R4–R7)_
- [x] **ISR-T3** Add focused tests and run the local 153/1,763 evaluation readiness check.
  _(→ISR-R1–R7)_
- [x] **ISR-T4** Record results and limitations in the project log without committing row-level
  output or private source material. _(→ISR-R6–R7)_

## Acceptance

The focused tests pass; all 153 expected identities bind to exactly one local source row; the
runner reads 1,763 candidates without writing a catalog; the aggregate report contains both
casting and exact-release metrics plus explicit authority/privacy limitations; only the final
153-row dataset from the collection process remains Git-tracked.
