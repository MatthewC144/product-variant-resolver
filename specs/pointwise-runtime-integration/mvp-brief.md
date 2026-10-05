# Pointwise runtime integration — MVP brief

Date: 2026-10-05. Mode: Lite / Lean Industrial. Status: **complete**.

## Purpose

Expose the frozen Pointwise release ranker through an explicit, local-only resolver configuration
without changing the default RRF path or treating neural logits as match probabilities. Activation
must fail closed until separately selected calibration and decision-policy artifacts are supplied.

## Observable requirements

- **PRI-R1 — Default preservation.** WHEN no neural opt-in is configured, THE SYSTEM SHALL keep
  reranking disabled and preserve the current RRF runtime behavior.
- **PRI-R2 — Pinned local loading.** WHEN `neural-pointwise-v1` is enabled, THE SYSTEM SHALL load
  only the approved local model directory, validate its pinned config, revision and file hashes,
  and make no network request.
- **PRI-R3 — Ranking parity.** WHEN neural reranking runs, THE SYSTEM SHALL use the same stable
  public candidate rendering and neural-logit ordering used by the frozen comparison, with RRF rank
  and canonical UUID as deterministic tie-breakers.
- **PRI-R4 — Policy isolation.** IF neural reranking is enabled without explicit neural-bound
  calibration and policy artifacts, THEN resolver construction SHALL fail closed.
- **PRI-R5 — Runtime evidence.** WHEN the neural path is active, debug and health responses SHALL
  expose the loaded pinned model version while retaining aggregate/privacy-safe observability.
- **PRI-R6 — Final-test immutability.** WHILE implementing runtime integration, THE SYSTEM SHALL NOT
  rerun the 53-case final test, change its artifacts, or tune against final-test answers.

## Design

`Settings` adds an allowlisted provider plus explicit config/model paths. A runtime adapter batches
all candidate pairs through the existing local `LocalPointwiseScorer`, applies the frozen candidate
renderer, writes ranking-only scores into the existing candidate debug fields and orders candidates
deterministically. `ResolverService` retains the lightweight heuristic as its disabled/default
ablation object and lazily loads the neural model only when explicitly enabled. Neural activation
also requires calibration/policy artifacts whose version metadata names `neural-pointwise-v1`.

## Tasks

- [x] **PRI-T1** Add fail-closed runtime settings and local neural loader. _(→PRI-R1, R2, R4)_
- [x] **PRI-T2** Add the batch Pointwise candidate adapter with frozen rendering/order semantics.
  _(→PRI-R3)_
- [x] **PRI-T3** Wire resolver debug/health metadata without changing defaults. _(→PRI-R1, R5)_
- [x] **PRI-T4** Add focused config, adapter and API regression tests; verify no final-test access.
  _(→PRI-R1–R6)_

## Acceptance

Default API tests remain unchanged. Direct neural-adapter tests prove stable pair rendering, score
assignment and tie-breaking. An enabled neural configuration without artifacts or with mismatched
artifact versions fails readiness. A fully bound test configuration exposes the pinned model
version. No image-search final-test runner is invoked.
