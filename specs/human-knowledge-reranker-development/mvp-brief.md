# Human Knowledge candidate-relative reranker — MVP brief

Date: 2026-09-20. Mode: Lite / Lean Industrial. Status: **implemented; no mitigation qualified**.

## Purpose and boundary

Develop admission v2 without tuning on the immutable private local-family evaluation. Retrieve a
larger public development candidate pool once, apply a frozen family of candidate-relative
unmatched-token penalties, and select at most one reranker that preserves every existing recall and
governance gate while reducing forbidden Top-5 neighbors.

## Requirements

- **HKRR-R1 — Freeze before measurement.** WHEN the experiment starts, THE SYSTEM SHALL freeze
  source hashes, the 25-candidate pool, seven penalty weights, formula, gates, and winner ordering
  before retrieving any grid result.
- **HKRR-R2 — Public development only.** Collection SHALL use exactly the committed 142-document
  corpus, 199-case existing development pack, and 24-case false-positive development pack; it SHALL
  NOT open a private projection or private evaluation artifact.
- **HKRR-R3 — Once-only retrieval.** THE SYSTEM SHALL execute exactly 223 retrieval calls at Top 25
  and reuse each raw candidate pool for every configuration.
- **HKRR-R4 — Candidate-relative penalty.** For each candidate, THE SYSTEM SHALL compute
  `rrf_score / (1 + weight * (1 - identity_token_coverage))`, sort deterministically, and take Top 5.
  It SHALL NOT hard-delete candidates based on coverage.
- **HKRR-R5 — Frozen grid.** THE SYSTEM SHALL compare weights `0`, `0.05`, `0.1`, `0.25`, `0.5`, `1`,
  and `2`; weight zero SHALL reproduce the source Top 5.
- **HKRR-R6 — Recall/governance gates.** An eligible configuration SHALL retain all 168 existing
  positive family hits, all four merge controls, zero existing held-family violations, zero unrelated
  nonempty results, all 24 new required hits, and zero retrieval errors.
- **HKRR-R7 — Deterministic selection.** Among eligible configurations, THE SYSTEM SHALL minimize
  new forbidden-hit cases, then maximize old and new rank-1 hits, then choose the lowest weight.
- **HKRR-R8 — Evidence integrity.** Raw scores, ranks, coverage, per-configuration results, gates,
  and winner SHALL be source-bound and reproducible; check mode SHALL never retrieve.
- **HKRR-R9 — Experimental only.** A selected configuration SHALL NOT modify the runtime retriever,
  API, PostgreSQL, canonical truth, release truth, or private evaluation.

## Design

`human_knowledge_reranker_development.py` owns a new immutable protocol and report. The existing v4
retriever supplies up to 25 candidates per query. Each candidate keeps its genuine sparse, dense,
character, and RRF evidence plus identity-token coverage. The reranker changes only ordering: a
candidate with unsupported identity tokens receives a weight-controlled multiplicative penalty,
while a fully supported candidate keeps its original score.

Using Top 25 is necessary because reordering a five-item pool cannot push an unsafe item out of Top
5. The weight-zero control proves the wider retrieval call preserves the original Top-5 ordering.
No new model or dependency is introduced.

## Tasks

- [x] **HKRR-T1** Implement and freeze protocol, raw serialization, and penalty formula. _(→R1–R5)_
- [x] **HKRR-T2** Implement once-only collection, scoring, gates, selection, and reports. _(→R3–R9)_
- [x] **HKRR-T3** Add unit, integrity, privacy-boundary, once-only, tamper, and artifact tests.
  _(→R1–R9)_
- [x] **HKRR-T4** Execute once, run QA, document the outcome and next gate, then push. _(→R1–R9)_

## Acceptance

The protocol was frozen before one 223-query collection, and all seven configurations preserved the
recall/governance gates. None reduced the 18 forbidden cases, so baseline is only a deterministic
fallback and v2 failed to qualify a mitigation. Runtime and private evaluation remain unchanged.
