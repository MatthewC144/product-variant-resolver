# AI Eval Result — fixture-v1

> Evaluated artifact: `evaluation-fixture-v1-test-rrf-default-v2`  
> Original evaluation date: 2026-09-01
> PostgreSQL retrieval update: 2026-09-07
> Outcome: **PASS for the Lite fixture and isolated PostgreSQL retrieval scopes; not production validation**

| Rubric item | Result | Evidence |
|---|---|---|
| Dataset disclosure | PASS | 21 synthetic test cases, 12 matched; scope disclaimer appears in JSON and Markdown. |
| Leakage control | PASS | Family-grouped split; train/dev guards passed; artifact records `test_labels_accessed=false`. |
| Retrieval | PASS | Offline fused evaluation, PostgreSQL FTS, and exact pgvector each achieved Recall@25 `1.0` = 12/12 on the matched frozen-test cases. |
| Ranking | PASS | Top-1 `1.0` = 12/12; hard-negative accuracy `1.0` = 4/4. |
| Reranker value | PASS via omission alternative | RRF Top-1 `1.0`; heuristic Top-1 `1.0`; gain `0.0`; RRF selected as default and heuristic retained only as opt-in ablation. |
| Abstention/reliability | PASS | Precision `1.0` (10/10), false-match rate `0.0` (0/9), coverage `0.8333` (10/12). |
| Latency honesty | PASS, limited | In-process ASGI p95 `7.9523 ms` remains separate from host→Docker loopback p95 `4.721208 ms`; both retain raw samples, warm-ups, method, and exclusions. |
| Failure safety | PASS WITH RISK | Missing catalog/provider, catalog checksum mismatch, one missing embedding row, and simulated/runtime retriever failure fail closed. Health does not actively poll the database after startup. |
| Runtime boundary | PASS, limited | Default image was verified on Docker 29.5.3/aarch64 and Python 3.12.14 as non-root/read-only. Separate isolated PostgreSQL 16.14 runs verified FTS and exact pgvector functionality, not database latency or concurrency. |

## Evidence pointers

- Machine-readable report: [`reports/fixture-v1/evaluation-fixture-v1-test.json`](../../../reports/fixture-v1/evaluation-fixture-v1-test.json)
- Human-readable report: [`reports/fixture-v1/evaluation-fixture-v1-test.md`](../../../reports/fixture-v1/evaluation-fixture-v1-test.md)
- Final QA mapping: [`specs/product-variant-resolver/review.md`](../../../specs/product-variant-resolver/review.md)
- Docker/Python 3.12 latency: [`reports/runtime-validation/docker-python312-http-latency.json`](../../../reports/runtime-validation/docker-python312-http-latency.json)
- PostgreSQL sparse evidence: [`docs/evidence/postgres-sparse-retrieval-t09.md`](../postgres-sparse-retrieval-t09.md)
- PostgreSQL exact dense evidence: [`docs/evidence/postgres-dense-retrieval-t10.md`](../postgres-dense-retrieval-t10.md)

## Non-passing / not-evaluated boundaries

- Pinned external embedding/cross-encoder models: not evaluated.
- PostgreSQL ingestion and retrieval are functionally evaluated at 120 rows; database latency,
  3,000-row behavior, concurrency/load, TLS, reverse proxy, and remote network are not evaluated.
- Rebuild reproducibility across time is not guaranteed; the Python 3.12 constraints are selective,
  not a complete transitive lock, and PostgreSQL extras/build dependencies remain range-resolved.
- Production accuracy, marketplace coverage, and production readiness: no claim.
