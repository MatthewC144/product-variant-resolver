# Local review-family anchored admission evaluation — MVP brief

Date: 2026-09-21. Mode: Lite / Lean Industrial. Status: **implemented; evaluation FAIL retained**.

## Purpose and boundary

Apply the publicly selected `secondary-075` policy to the immutable private 20-case shadow evidence
as a new versioned evaluation. Preserve the original v1 FAIL and raw retrieval exactly; execute no
new retrieval, do not tune the policy, and publish only privacy-safe aggregates.

## Requirements

- **LRAE-R1 — Frozen policy.** WHEN the evaluation begins, THE SYSTEM SHALL bind to the exact v3
  `secondary-075` selection, threshold `0.75`, protocol hash, and selection hash.
- **LRAE-R2 — Immutable upstream.** THE SYSTEM SHALL validate and checksum the existing private
  query pack, benchmark, raw result, scored result, five-document projection, and public v1 manifest
  without overwriting any upstream byte.
- **LRAE-R3 — No retrieval or tuning.** Evaluation SHALL execute zero retrieval calls and SHALL NOT
  change the policy after reading any private candidate, label, or result.
- **LRAE-R4 — Exact admission.** For each existing raw Top-5 row, source rank 1 SHALL be admitted;
  source ranks 2–5 SHALL require identity-token coverage at least `0.75`; source order SHALL remain.
- **LRAE-R5 — Precommitted gates.** PASS SHALL require positive Recall@5 = 1.0, positive Recall@1
  >= 0.8, local-family coverage@5 = 1.0, zero hard-negative forbidden hits, zero forbidden rank-1
  hits, zero upstream retrieval errors, and zero admission errors.
- **LRAE-R6 — Private/public split.** Queries, labels, candidate identities, coverage, ranks, and
  case results SHALL remain in a new ignored v2 directory. Public output SHALL contain only hashes,
  aggregate counts/metrics/gates, fixed policy, limitations, verdict, and zero downstream effects.
- **LRAE-R7 — Create once.** First scoring SHALL create new v2 private/public outputs. Exact rerun
  SHALL validate and return unchanged; partial, stale, or tampered state SHALL fail closed.
- **LRAE-R8 — Bounded meaning.** PASS SHALL authorize only opt-in runtime planning and API regression
  design. It SHALL NOT activate runtime knowledge, modify canonical truth, promote releases, fill
  color, or write PostgreSQL.

## Design

`release_casting_review_anchor_evaluation.py` verifies the original v1 one-shot evaluation and the
public v3 development selection. A public protocol then freezes every relevant file hash and the
private gates before v2 scoring. The scorer joins each old raw candidate UUID to the validated
147-document shadow catalog, computes the already frozen identity coverage, and applies the anchored
policy without calling the retriever.

The new private result is separate from v1 and contains per-case admitted/abstained ranks for audit.
The committed manifest and Markdown report expose no private query, expected label, candidate ID,
UUID, rank, coverage, or case ID. The old v1 evidence remains the immutable before measurement.

## Tasks

- [x] **LRAE-T1** Implement and freeze the v1/v3-bound private-evaluation protocol. _(→R1–R5)_
- [x] **LRAE-T2** Implement offline admission scoring and separate private/public publication.
  _(→R3–R8)_
- [x] **LRAE-T3** Add policy, gate, privacy, tamper, create-once, and real-artifact tests. _(→R1–R8)_
- [x] **LRAE-T4** Score once, run QA, document the verdict and next gate, then push public artifacts.
  _(→R1–R8)_

## Acceptance

The protocol preceded scoring, v1 bytes remain unchanged, and zero retrieval calls occurred. Positive
Recall@5 remains 15/15 and family coverage remains 5/5, but two forbidden families are source rank 1
and survive the anchor. The precommitted verdict is FAIL; runtime integration remains blocked.
