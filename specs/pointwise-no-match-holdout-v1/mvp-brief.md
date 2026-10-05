# Pointwise no-match holdout v1 — MVP brief

Date: 2026-10-05. Mode: Lite / Lean Industrial. Status: **complete and frozen; not scored**.

## Purpose

Turn the project owner's approved Batch 1 into a minimal, versioned 20-query no-match holdout.
Each query retains its casting-level and full release identity answer, while no image, source URL,
API response, timestamp or collection-only metadata enters the repository. This gate freezes test
truth only; it does not run the resolver or authorize model, threshold or runtime changes.

## Observable requirements

- **PNMH-R1 — Exact owner scope.** WHEN Batch 1 is materialized, THE SYSTEM SHALL contain exactly
  the 20 owner-reviewed queries and expected identities, and SHALL identify the state as
  `owner_reviewed_frozen_not_scored`.
- **PNMH-R2 — Catalog-relative absence.** Every expected brand-plus-casting family SHALL be absent
  under the project normalizer from the bound 1,763-record catalog SHA-256
  `b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4`.
- **PNMH-R3 — Minimal identity contract.** Every row SHALL contain only its ID, query,
  `expected_casting` and seven-field `expected_full_identity`; queries and castings SHALL be unique.
- **PNMH-R4 — Privacy and cleanup.** The tracked dataset SHALL NOT contain source/image URLs,
  image hashes, search times, raw API responses, color, edition or variant notes. Collection code,
  images and raw responses SHALL remain untracked and SHALL be deleted after verification.
- **PNMH-R5 — Fail-closed authorization.** Resolver scoring, model retuning, threshold retuning and
  runtime activation SHALL all remain explicitly unauthorized.
- **PNMH-R6 — Authority wording.** The dataset SHALL state that no-match is relative to a frozen
  third-party catalog and is not manufacturer-certified or global truth.

## Design and decision

The final artifact is one JSON dataset rather than a copy of the collection workspace. It preserves
only the inputs required for a later output-blind test: the natural-language query and its expected
casting/full identity. The catalog hash, deterministic candidate-pool hash and staged-review hash
bind its lineage without publishing source URLs or raw search material.

The 20 rows are frozen before any resolver access. Evaluation is intentionally a separate owner gate
so test results cannot influence membership, labels, features, model parameters or thresholds.

## Tasks

- [x] **PNMH-T1** Materialize the 20 approved rows as a versioned minimal dataset. _(→PNMH-R1, R3)_
- [x] **PNMH-T2** Bind and verify exact-family absence against the frozen catalog. _(→PNMH-R2, R6)_
- [x] **PNMH-T3** Encode explicit no-score/no-retune/no-runtime permissions. _(→PNMH-R5)_
- [x] **PNMH-T4** Add deterministic schema, integrity, privacy and absence tests. _(→PNMH-R1–R6)_
- [x] **PNMH-T5** Delete the untracked collection workspace after final verification. _(→PNMH-R4)_
- [x] **PNMH-T6** Record the decision, limitations and evidence in QA and Project Log.

## Acceptance

The final file must have SHA-256
`b46367efb54c9ab2a74c23d0824d1da5f939ecdf74a63c612da37c0688c50a7e`, contain 20 unique rows,
prove 20/20 exact normalized families absent from the bound catalog, expose none of the forbidden
collection fields and keep all four prohibited actions false. Tests must still pass after deletion
of the local collection workspace.
