# AI eval evidence — Serper dual-source raw Pointwise development v1

Date: 2026-10-10. Scope: development-only ranking ablation. Artifact SHA-256:
`f760d733ecc6cbee2124d42ad539d81b2f810bff2842ee26b2a2e6b2946df362`.

## Rubric and evidence

| Dimension | Criterion | Observed | Verdict |
| --- | --- | --- | --- |
| Dataset disclosure | Version, counts, split and authority scope are bound. | 150 paired targets; 100 development, 50 unopened test; 1,763 catalog candidates. | PASS |
| Leakage control | Test is not scored or used for selection. | `test_targets_scored=0`; selection used development only. | PASS |
| Retrieval | Report Recall@25 and preserve candidate membership. | Image 99%; Shopping 100%; Pointwise only reordered each RRF Top-25. | PASS |
| Ranking | Compare same-query RRF and Pointwise aggregate Top-1/MRR. | Image exact Top-1 39%→48%; Shopping 57%→74%; both MRR values improved. | PASS |
| Reranker value | At least +0.05 exact Top-1 or document omission. | +0.09 Image; +0.17 Shopping. | PASS |
| Latency honesty | Measure only CPU rerank time and disclose boundary. | Pointwise p95: Image 130.205 ms, Shopping 124.224 ms; excludes retrieval/API transport/concurrency. | PASS |
| Model integrity | Frozen local model and prior selection must validate; no refit. | MiniLM revision and manifest validated; `model_refit=false`. | PASS |
| Output minimization | No row-level query, target, candidate or prediction. | Aggregate counts and metrics only. | PASS |
| Runtime boundary | Development selection must not activate policy/runtime. | No calibration/policy scoring, threshold change or runtime activation. | PASS |

## Interpretation

The result supports a development claim that the frozen neural Pointwise reranker improves ranking
over the existing RRF order for both Serper-derived raw query sources. It does not yet support a
final generalization claim: the 50-target grouped, year-stratified test partition remains unopened.
It also does not establish match/no-match reliability because no calibration or decision policy was
evaluated. The Pointwise p95 figures are local sequential CPU rerank measurements over at most 25
candidates, not end-to-end service or production latency.
