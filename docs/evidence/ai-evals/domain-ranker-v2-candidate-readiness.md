# Domain ranker v2 candidate readiness — AI-eval rubric

Date: 2026-10-10. Scope: DRV2-T3–T3R. Verdict: **PIPELINE AND EQUIVALENT LATENCY REPAIR PASS; NO MODEL-QUALITY CLAIM**.

| Rubric | Evidence | Result |
|---|---|---|
| Frozen lineage | T2 query pack, catalog, generic config/manifest/weights and implementation commit hash-bound | PASS |
| Query-only retrieval | 180 pools, 4,500 candidates, target-injection count 0 | PASS |
| Retrieval coverage | train/validation/selection miss counts all 0 | PASS |
| Selection isolation | selection quality evaluations 0; latency uses validation only | PASS |
| Generic latency | T3 PyTorch p95 `217.699834 ms`; T3R ONNX p95 `103.654042 ms` | PASS after repair |
| Inference equivalence | 4,500 pairs ≤`2e-5` delta; 180/180 Top-25 orderings identical | PASS |
| Claim discipline | hard-negative labels 0, training runs 0, runtime unchanged | PASS |
| Publication boundary | public aggregate only; local row-level pool mode `0600` and Git-ignored | PASS |

The generic scorer successfully produced frozen relevance logits for the query-only pools, but this
does not establish model improvement, calibration or production readiness. The initial latency
failure remained binding until a separately governed implementation-only repair passed the
identical benchmark while preserving score/rank equivalence.

T3R satisfied that repair boundary with a float32, non-quantized ONNX export. It changed the
inference substrate only and left model weights, tokenizer, query/candidate inputs, Top-25 membership
and ranking order unchanged. The result establishes generic latency readiness for the experiment;
it does not establish domain-ranker improvement and does not activate the backend in runtime.
