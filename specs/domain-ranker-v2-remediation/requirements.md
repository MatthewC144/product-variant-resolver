# Domain ranker v2 remediation — Requirements

Date: 2026-10-10. Mode: Lite / Lean Industrial. Status: **DRV2-T0–T4 complete; T5+ not authorized**.

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

## T1 governance result

The frozen capacity audit excludes all 153 existing positive identities and binds 173 existing
positive/negative query hashes as a permanent denylist. It leaves 1,610 catalog rows, of which 1,041
rows across 269 casting families meet the preregistered authoring-capacity rule. The public protocol
projects only casting and exact-release fields, keeps color/edition unauthorized, prohibits resolver
or T5-error access and keeps every future row-level query local-only.

Governance content SHA-256 is
`5b981e79df16510210b529a299932dc52c54b3b776808f792433f002eb7d03f8`.
T1 performed no query materialization, partitioning, candidate scoring, mining or training.

## T2 Owner Gate

The owner's next-step instruction authorizes DRV2-T2 only. T2 SHALL deterministically author exactly
180 new local-only queries from 180 distinct eligible casting families and freeze them as 120 train,
30 validation and 30 untouched selection rows. Git may retain authorization, hashes and aggregate
counts only. This Gate does not authorize candidate pools, scoring, hard-negative labels, training,
calibration, final evaluation or runtime activation.

## T2 result

T2 froze 180 unique queries, exact identities and casting families as 120 train, 30 validation and
30 untouched selection rows. Query, exact-identity and casting-family overlap across partitions are
all zero. All 120 train families retain at least two eligible same-family sibling releases, so the
future density gate has sufficient candidates without yet treating any sibling as a labeled
negative. Row-level data is mode-0600 and Git-ignored; three public files contain authorization,
hashes and aggregate counts only. T3 and all scoring remain separately gated.

## T3 Owner Gate

The owner's next-step instruction authorizes DRV2-T3 only. T3 SHALL retrieve and freeze exactly one
query-only Top-25 pool for each of the 180 T2 rows, score those fixed pools once with the pinned
generic MiniLM and measure CPU latency on the 30 validation rows only. The benchmark SHALL use one
CPU thread, batch size 25, three warm-ups, three rounds and nearest-rank p95 over 90 samples. If p95
exceeds 200 ms, T3 SHALL publish a failed readiness status and stop before T4. This Gate does not
authorize hard-negative labels, model training, selection evaluation, calibration or runtime.

## T3 result

T3 froze 180 query-only Top-25 pools containing 4,500 candidates. Retrieval found every expected
identity without target injection: train, validation and selection retrieval-miss counts are all
zero. The fixed 90-sample validation benchmark measured generic CPU p50 `183.735 ms` and p95
`217.699834 ms`. Because p95 exceeds the unchanged `200 ms` budget, DRV2-R8 failed and T4 is blocked.
A separately authorized T3R may change only the inference implementation; it must prove score/order
equivalence and rerun the identical benchmark before any labels or training are created.

## T3R Owner Gate

The owner's next-step instruction authorizes a latency-only T3R. The repair SHALL export the pinned
generic safetensors checkpoint to float32 ONNX opset 17 without quantization. Before timing is
accepted, all 4,500 frozen logits SHALL differ from the PyTorch baseline by at most `2e-5` and all
180 complete Top-25 orderings SHALL be identical under the frozen UUID tie-break. T3R SHALL then run
the unchanged 90-sample validation benchmark with the same `≤200 ms` p95 gate. The ONNX graph stays
local-only; Git retains exact dependencies, export code, artifact hash and aggregate results. T4
still requires separate authorization even if T3R passes.

## T3R result

The formal float32 ONNX export passed both equivalence gates: all 4,500 logits stayed within
`1.4781951904296875e-05` maximum absolute delta and all 180 complete Top-25 orderings matched the
frozen PyTorch baseline. The identical 90-sample validation protocol measured p50 `88.765583 ms`
and p95 `103.654042 ms`, a p95 reduction of `114.045792 ms` (`52.39%`) from T3. DRV2-R8 now passes.
The graph remains local-only and mode `0600`; public output contains its SHA, reconstruction
dependencies and aggregate results. At this T3R checkpoint, T4 remained separately gated.

## T4 Owner Gate

The owner's next-step instruction authorizes DRV2-T4 only. T4 SHALL use only the 120 train queries
and their frozen Top-25 pools. A sibling may become a negative only when it has the same normalized
casting and conflicts with at least one exact-release field explicitly present in that query's
frozen template. Generic score or rank may order evidence-qualified rows for audit, but SHALL NOT
create a label. A query is admitted only when it has at least two defensible siblings; ambiguous or
insufficient-density siblings remain held. This Gate does not authorize model training, validation
early stopping, selection scoring, calibration, final evaluation or runtime activation.

## T4 result

Of 120 train queries, 112 have at least two defensible same-casting wrong-release siblings, exceeding
the DRV2-R4 minimum of 60. These qualifying queries produce 332 pairwise triples from 340 defensible
siblings; the eight otherwise defensible siblings belonging to eight one-negative queries remain
held because their query does not meet the two-negative density rule. Another 19 same-casting
siblings remain held because no query-supported exact field distinguishes them. The resulting 27
held records are not forced into binary labels. Validation and selection label reads, training runs
and selection evaluations are all zero. Row-level triples remain Git-ignored and mode `0600`; the
public manifest contains hashes and aggregate counts only. T5 requires a separate Owner Gate.
