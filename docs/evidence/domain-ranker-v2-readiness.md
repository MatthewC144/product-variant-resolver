# Domain ranker v2 remediation readiness

Date: 2026-10-09. Scope: planning evidence only. Verdict: **READY FOR OWNER REVIEW; NOT AUTHORIZED
FOR EXECUTION**.

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

T2 query materialization/partitioning remains separately gated. Model scoring, mining, training,
calibration, final evaluation and runtime actions remain zero.
