# Neural reranker comparison v1

Winner: **null**. Runtime default remains **RRF**.

Dataset: 100-case synthetic/curated fixture benchmark; Test has 21 cases and exactly 12 matched ranking targets. One matched case changes Top-1 by 0.0833.

| Arm | Top-1 | MRR@10 | Hard-negative | Recall@25 | Resolver p95 ms |
|---|---:|---:|---:|---:|---:|
| rrf | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.398 |
| neural_pointwise | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 89.164 |
| neural_listwise | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 89.583 |

## Limitations

- Shadow evaluation only; runtime, API, calibration, Dual RAG and PostgreSQL are unchanged.
- The 12 matched Test cases do not establish production accuracy or statistical generality.
- A null result is complete and must not be retuned against Test labels.

All metrics preserve raw numerators and denominators in comparison.json.
