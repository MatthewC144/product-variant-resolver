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
| Latency honesty | PASS, limited | In-process ASGI p95 `7.9523 ms` remains separate from host→Docker loopback p95 `4.721208 ms`; both retain raw samples, warm-ups, method, and exclusions. |
| Failure safety | PASS WITH RISK | Missing catalog/provider and simulated retriever failure fail closed; runtime readiness transition after a post-start failure was not verified. |
| Runtime boundary | PASS, limited | Default image verified on Docker 29.5.3/aarch64 and Python 3.12.14 as non-root/read-only; 50 sequential loopback samples at concurrency 1. |

## Evidence pointers

- Machine-readable report: [`reports/fixture-v1/evaluation-fixture-v1-test.json`](../../../reports/fixture-v1/evaluation-fixture-v1-test.json)
- Human-readable report: [`reports/fixture-v1/evaluation-fixture-v1-test.md`](../../../reports/fixture-v1/evaluation-fixture-v1-test.md)
- Final QA mapping: [`specs/product-variant-resolver/review.md`](../../../specs/product-variant-resolver/review.md)
- Docker/Python 3.12 latency: [`reports/runtime-validation/docker-python312-http-latency.json`](../../../reports/runtime-validation/docker-python312-http-latency.json)

## Non-passing / not-evaluated boundaries

- PostgreSQL/pgvector retrieval and ingestion: not evaluated.
- Pinned external embedding/cross-encoder models: not evaluated.
- TLS, reverse proxy, remote network, concurrency/load, and PostgreSQL runtime: not evaluated.
- Rebuild reproducibility across time: not guaranteed; dependency ranges are not frozen by a
  lockfile or constraints file, and the dev extra retains legacy `httpx`.
- Production accuracy, marketplace coverage, and production readiness: no claim.
