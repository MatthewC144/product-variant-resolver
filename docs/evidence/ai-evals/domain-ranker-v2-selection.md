# AI eval evidence — Domain ranker v2 selection

Date: 2026-10-10. Gate: DRV2-T6/T7. Result SHA-256:
`2f4a32fbb0383bcd934af48734d6e60ab6603bc03093a084d5cdb552194dbefc`.

## Rubric and evidence

| Dimension | Frozen criterion | Observed | Verdict |
|---|---|---|---|
| Dataset disclosure | 120/30/30 construction, catalog-relative/synthetic limitation and source hashes visible | 180 unique queries, identities and families; zero cross-partition overlap | PASS |
| Leakage control | Validation only for early stopping; selection once after protocol commit | Validation selected epochs; one 30-row selection evaluation after `5e67fbb` | PASS |
| Retrieval | Target appears naturally in every Top-25 pool | 30/30 selection targets present; no target injection | PASS |
| Inference equivalence | Each domain ONNX export: max logit delta ≤`2e-5`, 30/30 identical orders | `1.1921e-05` and `1.0490e-05`; both 30/30 | PASS |
| Casting and recall | No casting regression beyond one case; Recall@25 does not fall | All arms 30/30 casting and 30/30 Recall@25 | PASS |
| Reranker value | +3 exact cases, +0.02 MRR, +0.10 same-family; both seeds positive | Best arm only +1, +0.0167, +0.0115; second seed regressed | **FAIL** |
| Latency honesty | Identical CPU runtime; domain p95 ≤200 ms and ≤1.25x generic | 121.251/114.842 ms vs 106.127 ms generic | PASS |
| Output privacy | Public artifacts contain no row-level query, target, candidates or prediction | Aggregate-only; local artifacts ignored and `0600` | PASS |
| Runtime boundary | No calibration, final evaluation, policy or runtime activation after null winner | All counters zero; default remains disabled heuristic path | PASS |

## Evaluation judgment

The evaluation process passes, but the model qualification fails. This distinction matters: the
training pipeline and artifacts are reproducible, while the measured fine-tuned models do not add
enough value to displace generic MiniLM. `winner: null` is therefore the only rubric-compliant
result. The experiment supplies AI-engineering evidence without converting a small, insufficient
gain into a deployment claim.

Closure verification recorded 44 passing T1–T7 tests and 70 passing tests when config/FastAPI
regressions are included. The repository-wide smoke run was stopped at 102 passes and the same 13
pre-existing experimental human-storage API failures disclosed in the Lite review; these are outside
the ranker v2 scope and do not alter the null-winner decision.
