# Domain ranker v2 remediation readiness

Date: 2026-10-09. Scope: DRV2-T0–T3. Verdict: **POOL READINESS PASS; GENERIC LATENCY FAIL; T4 BLOCKED**.

## Why a new version is required

DRSP-T5 is immutable and selected no checkpoint. Both domain seeds moved exact Top-1 from `24/30`
to `23/30`, MRR@10 from `0.87777778` to `0.86111111`, and same-family accuracy from `41/52` to
`40/52`. Calibration cannot repair rank ordering, and changing the v1 gates after inspection would
invalidate the experiment. Any further training must therefore be a new version with new evidence,
new hashes and a new Owner Gate.

## Evidence-backed remediation

V1 provided 345 training pairs, but 207 were adjacent-year/wrong-series-or-identifier while only 67
were same-casting wrong-exact. Sixty-five additional same-family candidates were held because the
query did not support a defensible exact-release decision. Both seeds peaked at epoch 1 and then lost
selection MRR as training loss continued downward. These facts motivate—without proving—a v2 test
of more exact-release-focused data and a pairwise ordering objective.

The proposed minimum is 180 newly authorized queries split by connected components into at least
120 train, 30 validation and 30 untouched selection rows. At least 60 train queries must each support
two defensible same-casting negatives. A generic latency readiness check occurs before any training,
because all v1 arms—not only domain checkpoints—missed the 200 ms budget.

## Still prohibited

No existing holdout or T2 selection error may be used to author v2 labels, mine negatives or tune the
objective. This readiness document does not authorize collection, scoring, training, checkpoint
publication, calibration, final evaluation or runtime activation.

## T1 governance result

The source-capacity audit and authoring protocol are now materialized. All 153 existing positive
identities are excluded, and query hashes from the 153-positive dataset plus 20-negative holdout form
a 173-query denylist. After identity exclusion, 1,610 catalog rows remain; 1,041 rows in 269
multi-release casting families meet the field-density rule. This is capacity evidence, not a query
dataset or training label package.

- Authorization file SHA-256:
  `d42ab9415c66c24b986731292ff9a9d02f4dd46a974b57c9cd0a4b3bfa8e3fab`.
- Authoring protocol file SHA-256:
  `9d56b2d2ad524159b5334b9b1a3aab321954e6153a3ae5afe5ca9935806be4fc`.
- Governance file SHA-256:
  `66bbe6f660492a372e2a7dce70ba126b849913efd25c952e389886dbc73ca3d6`.
- Governance content SHA-256:
  `5b981e79df16510210b529a299932dc52c54b3b776808f792433f002eb7d03f8`.

## T2 query and partition result

The approved deterministic authoring run selected one release from each of 180 different eligible
casting families and generated 180 unique local-only queries. It froze 120 train, 30 validation and
30 untouched selection rows. Cross-partition normalized-query, exact-identity and casting-family
overlap counts are all zero. All 120 train rows retain at least two other eligible same-family
releases, exceeding the 60-query capacity minimum for the later density gate; no negative label was
created in T2.

- Query-pack content SHA-256:
  `149d7d867b9e270ffb805906aec64685d6823f11efcd68a59e9e74ba60134e6f`.
- Private query-pack file SHA-256:
  `8f52043d615c1422018e5abe01670ba867c1908a6b268ce85754c71a9528d1fa`.
- T2 authorization content SHA-256:
  `c888605084e0f596a135bb13b62b72c12b614f246677b467b4754f35e8f40099`.
- Query manifest content SHA-256:
  `26babd4c925e341e72f3bb297c9824eb4ed9d647263f84fae4a5351094faf825`.
- Split manifest content SHA-256:
  `bebcaa059212081fe465d102b5a0ae1626508ea3104471bbd8311703d099b73d`.

The private pack is Git-ignored and mode `0600`; public artifacts contain aggregate counts and hashes
only. Model scoring, mining, training, calibration, final evaluation and runtime actions remain zero.
DRV2-T3 requires a separate Owner Gate.

## T3 candidate-pool and latency result

The query-only retrieval run froze 180 Top-25 pools and 4,500 candidates. It found every target in
the unmodified retrieval output: train, validation and selection miss counts are all zero, and target
injection count is zero. The generic model is the unchanged revision-pinned
`cross-encoder/ms-marco-MiniLM-L6-v2`; no domain checkpoint was loaded.

On Darwin arm64 with CPython 3.12.13, Torch 2.7.1, Transformers 4.57.6 and Sentence Transformers
3.4.1, the frozen one-thread CPU protocol measured 90 validation samples: p50 `183.735 ms`, p95
`217.699834 ms`. The unchanged gate is p95 `≤200 ms`, so readiness failed and T4 remains blocked.

- T3 authorization content SHA-256:
  `ef8a7215f336443f58162b0f66138a5e449bda3245e2af5a43e88d2f045195c3`.
- Candidate-pool manifest content SHA-256:
  `da419555a6e364063a288a7ece691a330f849d361b7735809e616af4d4310777`.
- Private pool artifact SHA-256:
  `0c889bfc06755a49ba779f2df64a4e4d87d3de676bf47063fcfcdec454022b24`.
- Latency readiness content SHA-256:
  `7b396578d36e8c6a76fd79e447770713014716aa911661f4055898f2f0c76d86`.

Public artifacts contain only bindings, aggregate counts, environment and latency metrics. The
row-level pools remain Git-ignored and mode `0600`. T3R must be separately authorized and may not
change weights, inputs, ranking semantics or the 200 ms threshold.
