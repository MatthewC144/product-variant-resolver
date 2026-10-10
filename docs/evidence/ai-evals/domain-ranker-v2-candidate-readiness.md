# Domain ranker v2 candidate readiness — AI-eval rubric

Date: 2026-10-09. Scope: DRV2-T3 only. Verdict: **PIPELINE PASS; LATENCY FAIL; NO MODEL CLAIM**.

| Rubric | Evidence | Result |
|---|---|---|
| Frozen lineage | T2 query pack, catalog, generic config/manifest/weights and implementation commit hash-bound | PASS |
| Query-only retrieval | 180 pools, 4,500 candidates, target-injection count 0 | PASS |
| Retrieval coverage | train/validation/selection miss counts all 0 | PASS |
| Selection isolation | selection quality evaluations 0; latency uses validation only | PASS |
| Generic latency | p95 `217.699834 ms` versus fixed `≤200 ms` | FAIL |
| Claim discipline | hard-negative labels 0, training runs 0, runtime unchanged | PASS |
| Publication boundary | public aggregate only; local row-level pool mode `0600` and Git-ignored | PASS |

The generic scorer successfully produced frozen relevance logits for the query-only pools, but this
does not establish model improvement, calibration or production readiness. The latency failure is
binding: T4 mining and all training remain blocked until a separately governed implementation-only
repair passes the identical benchmark while preserving score/rank equivalence.
