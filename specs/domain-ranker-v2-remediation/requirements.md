# Domain ranker v2 remediation — Requirements

Date: 2026-10-09. Mode: Lite / Lean Industrial. Status: **DRV2-T1 authorized; source/authoring
governance implementation in progress; T2+ not authorized**.

## Goal

Design one new, independently gated domain-ranker experiment that addresses the DRSP-T5 negative
result without retuning on the frozen T2 selection outcomes. V2 is not a continuation of T5 and may
not reinterpret either failed checkpoint as selected.

## Evidence boundary

The frozen T5 result remains `winner: null`. Generic achieved exact Top-1 `24/30`, MRR@10
`0.87777778` and same-family accuracy `41/52`; both domain seeds achieved `23/30`, `0.86111111` and
`40/52`. Both seeds selected epoch 1, while later epochs lowered training loss but reduced selection
MRR. Of 345 v1 training pairs, 207 were adjacent-year/wrong-series-or-identifier and 67 were
same-casting wrong-exact; 65 additional same-family candidates were held for insufficient evidence.

These observations support, but do not prove, the hypothesis that v1 was data-limited and that
independent binary relevance did not sufficiently optimize within-family release ordering. V2 must
test that hypothesis on new development evidence rather than inspect or relabel T5 errors.

## Observable requirements

- **DRV2-R1 — New authorization boundary.** WHEN v2 data is proposed, THE SYSTEM SHALL require a new
  checksum-bound Owner Gate naming source hashes, training rights, label authority, permitted uses,
  publication scope and retention. V1 authorization SHALL NOT be inherited implicitly.
- **DRV2-R2 — Permanent holdout isolation.** THE SYSTEM SHALL keep the opened 53-positive test,
  20-negative holdout, 52 no-match development rows and frozen T2 ranker-selection rows out of v2
  mining, fitting, early stopping and model selection.
- **DRV2-R3 — New-data readiness.** BEFORE v2 training, THE SYSTEM SHALL admit at least 180 new
  catalog-present queries and form connected-component-disjoint partitions with at least 120 ranker
  train, 30 early-stop validation and 30 model-selection rows.
- **DRV2-R4 — Exact-release evidence density.** BEFORE v2 training, at least 60 train queries SHALL
  contain an authoritative query-supported exact-release discriminator and at least two defensible
  same-casting wrong-release candidates. Evidence-insufficient siblings SHALL remain held.
- **DRV2-R5 — Pairwise primary hypothesis.** WHEN v2 training begins, THE SYSTEM SHALL use one
  preregistered pairwise ranking objective over query/positive/negative triples. It SHALL NOT search
  Pointwise, Pairwise and Listwise objectives on the same selection partition.
- **DRV2-R6 — Validation/selection separation.** THE SYSTEM SHALL use only the v2 validation
  partition for early stopping and only the untouched v2 selection partition for generic/domain
  winner qualification.
- **DRV2-R7 — Frozen retrieval and candidate pools.** WHEN v2 pools are created, THE SYSTEM SHALL
  bind catalog, renderer, retrievers, generic model, Top-K and implementation hashes. Expected
  identities SHALL NOT be injected when retrieval misses.
- **DRV2-R8 — Latency readiness before training.** BEFORE fitting a v2 checkpoint, THE SYSTEM SHALL
  record a hardware/runtime manifest and confirm the pinned generic arm meets the unchanged 200 ms
  CPU p95 budget under the frozen benchmark procedure. IF generic itself fails, THEN the run SHALL
  stop for environment/procedure repair before model training.
- **DRV2-R9 — Predeclared qualification.** BEFORE any v2 selection score is visible, THE SYSTEM SHALL
  freeze exact Top-1, casting Top-1, MRR@10, Recall@25, same-family accuracy, latency and two-seed
  gates, including deterministic tie handling and winner selection.
- **DRV2-R10 — Negative result preservation.** IF no v2 checkpoint passes every frozen gate, THEN
  THE SYSTEM SHALL publish `winner: null` and SHALL NOT start calibration, final evaluation or
  runtime activation.
- **DRV2-R11 — Aggregate-only reporting.** Public v2 reports SHALL contain aggregate metrics,
  lineage and limitations only. Row-level queries, predictions, errors and split membership SHALL
  remain local and Git-ignored unless a separate disclosure Gate is approved.
- **DRV2-R12 — Claim discipline.** V2 evidence SHALL distinguish a working training pipeline from
  measured model improvement and SHALL retain community-catalog-relative, non-manufacturer truth.

## Owner decisions required before execution

1. Approve or revise the minimum 180-query acquisition target and 120/30/30 split.
2. Approve a specific new-data source and its training/publication rights.
3. Approve pairwise ranking as the single v2 objective and its fixed loss/hyperparameters.
4. Approve the v2 quality gates before selection scores are visible.
5. Confirm that v2 may publish minimized training triples and safetensors only after new release
   Gates; no permission is inferred from v1 packages.

The owner's next-step instruction after this five-item handoff authorizes DRV2-T1 to bind the frozen
catalog source and an owner-authored synthetic query protocol. It does not authorize query
materialization, partitioning, scoring, mining, training or publication. Source rights and authority
remain owner-attested and community-catalog-relative, not independently verified or manufacturer
truth.
