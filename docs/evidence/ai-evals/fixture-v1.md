# AI Eval Result — fixture-v1

> Evaluated artifact: `evaluation-fixture-v1-test-rrf-default-v2`  
> Date: 2026-09-01  
> Outcome: **PASS for the Lite offline fixture scope; not production validation**

| Rubric item | Result | Evidence |
|---|---|---|
| Dataset disclosure | PASS | 21 synthetic test cases, 12 matched; scope disclaimer appears in JSON and Markdown. |
| Leakage control | PASS | Family-grouped split; train/dev guards passed; artifact records `test_labels_accessed=false`. |
| Retrieval | PASS | Recall@25 `1.0` = 12/12. |
| Ranking | PASS | Top-1 `1.0` = 12/12; hard-negative accuracy `1.0` = 4/4. |
| Reranker value | PASS via omission alternative | RRF Top-1 `1.0`; heuristic Top-1 `1.0`; gain `0.0`; RRF selected as default and heuristic retained only as opt-in ablation. |
| Abstention/reliability | PASS | Precision `1.0` (10/10), false-match rate `0.0` (0/9), coverage `0.8333` (10/12). |
| Latency honesty | PASS, limited | Latest checked-in warmed in-process ASGI p95 `7.9523 ms`, 21 samples after five warm-ups, K=25; exclusions explicitly recorded. |
| Failure safety | PASS WITH RISK | Missing catalog/provider and simulated retriever failure fail closed; runtime readiness transition after a post-start failure was not verified. |

## Evidence pointers

- Machine-readable report: [`reports/fixture-v1/evaluation-fixture-v1-test.json`](../../../reports/fixture-v1/evaluation-fixture-v1-test.json)
- Human-readable report: [`reports/fixture-v1/evaluation-fixture-v1-test.md`](../../../reports/fixture-v1/evaluation-fixture-v1-test.md)
- Final QA mapping: [`specs/product-variant-resolver/review.md`](../../../specs/product-variant-resolver/review.md)

## Non-passing / not-evaluated boundaries

- PostgreSQL/pgvector retrieval and ingestion: not evaluated.
- Pinned external embedding/cross-encoder models: not evaluated.
- Docker/Python 3.12 runtime, TCP/network, database, concurrency, and load: not evaluated.
- Production accuracy, marketplace coverage, and production readiness: no claim.
