# AI eval evidence — Serper dual-source raw Pointwise final test v1

Date: 2026-10-10. Evaluation: SDSE-T4. Result SHA-256:
`ba06ef6db36e86d436205af82b7d96f2af902c4f082194acfe006af470ba37e2`.

## Rubric and evidence

| Dimension | Frozen criterion | Observed | Verdict |
| --- | --- | --- | --- |
| Owner gate | Explicit authorization bound to dataset, split and development winner. | Authorization SHA `b22e…fc14` validated before scoring. | PASS |
| Test isolation | 50 grouped test targets remain unopened until the one authorized run. | One completed run; development targets scored in final run: 0. | PASS |
| One-shot safety | A completed artifact prevents another run before data/model loading. | `completed_test_run_count=1`, `rerun_allowed=false`; guard test passes. | PASS |
| Candidate parity | Pointwise may only reorder each query's RRF Top-25. | No candidate membership changes; Recall@25 directly comparable. | PASS |
| Ranking value | Report same-case RRF and Pointwise Top-1/MRR for both sources. | Combined exact Top-1 55%→64%; MRR@10 0.722→0.792. | PASS |
| Retrieval disclosure | Report any Recall tradeoff, not only gains. | Recall@25 stayed 99%; Recall@10 99%→98%, driven by Image 98%→96%. | PASS |
| Model integrity | Use the preselected frozen local model with no final adaptation. | MiniLM revision/manifest matched; no refit, calibration or threshold change. | PASS |
| Output minimization | Persist aggregate counts/metrics only. | No row-level query, label, candidate, confidence or prediction. | PASS |
| Runtime boundary | Ranking evidence must not imply an activated resolver policy. | Runtime unchanged; policy claim and activation remain disallowed. | PASS |

## Final metrics

| Source | Ranker | Casting Top-1 | Exact Top-1 | Recall@10 | Recall@25 | MRR@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Image raw | RRF | 80% | 50% | 98% | 98% | 0.690 |
| Image raw | Pointwise | 92% | 56% | 96% | 98% | 0.744 |
| Shopping raw | RRF | 92% | 60% | 100% | 100% | 0.754 |
| Shopping raw | Pointwise | 98% | 72% | 100% | 100% | 0.841 |

## Interpretation

The untouched grouped test confirms that the development-selected frozen Pointwise reranker
generalizes its Top-1 and MRR advantage to both Serper-derived raw query sources. The honest final
claim includes the Image Recall@10 regression: Pointwise moved one exact target below rank 10 while
keeping it inside the unchanged Top-25 candidate set. The test supports a ranking architecture
choice, not a match/no-match production policy. Calibration, abstention, thresholds, concurrency,
end-to-end API latency and runtime activation were outside SDSE-T4.
