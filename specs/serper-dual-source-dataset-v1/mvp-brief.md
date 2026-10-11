# Serper dual-source query dataset v1 — MVP brief

Date: 2026-10-10. Mode: Lite / Lean Industrial. Status: **complete**.

Owner authorization: collect new resolver benchmark queries with the owner-provided Serper key,
using both image-search/Lens and Google Shopping. The key and all temporary collection material must
remain local; only the minimized final dataset may be committed.

## Purpose

Build a source-grounded benchmark that preserves provider text both before and after deterministic
cleaning. Sample 150 release targets from the frozen 1,763-row community catalog, then produce one
image-search-derived query and one Shopping-derived query for each target. This creates 300 paired
records and four future evaluation arms: image raw, image cleaned, Shopping raw, and Shopping
cleaned.

## Observable requirements

- **SDS-R1 — Paired targets.** THE COLLECTOR SHALL retain exactly 150 target identities and exactly
  two records per target, one `image_search` and one `shopping`; a target pair must remain together
  in any future split.
- **SDS-R2 — Minimal row contract.** EACH record SHALL contain only `id`, `target_id`, `source_type`,
  `query_raw`, `query_cleaned`, `expected_casting`, and `expected_full_identity`.
- **SDS-R3 — Source-grounded answer.** `expected_casting` and every populated full-identity field
  SHALL come directly from the selected row in the frozen 1,763-row catalog. The answer is
  catalog-relative, not manufacturer/global truth.
- **SDS-R4 — Real provider text.** `query_raw` SHALL be a selected Serper result title before local
  identity cleaning. `query_cleaned` SHALL be the deterministic normalization of that same title;
  neither value may be synthesized from the expected answer.
- **SDS-R5 — Acceptance gate.** A pair SHALL be retained only when both provider titles carry enough
  lexical or toy-number evidence for the sampled target. Insufficient or wrong-product results are
  rejected and replaced by another sampled target rather than relabeled.
- **SDS-R6 — Secret and temporary-data boundary.** THE WORKFLOW SHALL read the key from the existing
  local `.env`, never print or persist it, keep URLs/images/raw responses/checkpoints in a
  Git-ignored temporary directory, and remove that directory after final validation.
- **SDS-R7 — Request budget.** THE WORKFLOW SHALL stop before 900 Serper attempts and expose only
  aggregate call/success/failure counts. This cap includes non-credit HTTP failures and remains far
  below the owner-stated 2,500-credit limit.
- **SDS-R8 — No premature evaluation.** Collection and dataset validation SHALL NOT tune or run the
  resolver, choose thresholds, or activate runtime behavior.

## Design

```text
ignored 1,763-row snapshot
  -> deterministic candidate order; exclude v1 benchmark castings
  -> Serper Images target lookup -> one selected public image URL (temporary only)
  -> Serper Lens -> selected raw title -> deterministic cleaned title
  -> Serper Shopping -> selected raw title -> deterministic cleaned title
  -> pair-level evidence gate
  -> minimized 300-row tracked dataset with aggregate top-level metadata
  -> delete ignored collection workspace
```

The two channels share the same 150 target rows. URLs and provider payloads exist only long enough
to make collection resumable and are not part of the benchmark. Selection may use the expected
casting/toy number only as an acceptance gate; it cannot rewrite provider text or invent a label.

## Tasks

- [x] **SDS-T1** Freeze the schema, safety boundary, acceptance rule and request budget.
  _(→SDS-R1–R8)_
- [x] **SDS-T2** Probe the Images/Lens and Shopping response schemas without exposing the key or raw
  payloads. _(→SDS-R4,SDS-R6–R7)_
- [x] **SDS-T3** Collect and checkpoint accepted target pairs in the ignored workspace.
  _(→SDS-R1,SDS-R3–R7)_
- [x] **SDS-T4** Materialize and validate the minimized 300-row dataset.
  _(→SDS-R1–R8)_
- [x] **SDS-T5** Remove all temporary collection material and record the decisions and evidence in
  the project log. _(→SDS-R6–R8)_

## Acceptance

Exactly 150 target IDs have one record from each source; all 300 rows have non-empty, paired raw and
cleaned strings and exact source-row identities; no forbidden field or secret exists in tracked
files; request attempts are below 900; the temporary workspace is absent; focused schema/privacy tests
pass; no resolver evaluation or runtime change occurred.
