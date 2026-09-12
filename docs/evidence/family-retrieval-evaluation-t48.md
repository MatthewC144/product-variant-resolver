# Family Retrieval Evaluation T48 — Closure Evidence

> Mode: Lite / Lean Industrial
>
> Date: 2026-09-12
>
> Milestone: T48.1–T48.5 complete
>
> Quality verdict: **FAIL; T49 not authorized**

## What T48 established

T48 replaced the leaky T47 exact-name smoke matrix with a separately authored, project-owner-
approved test boundary. The query pack was committed before labels, the labeled benchmark was
committed before retrieval, and the first scored run evaluated the already frozen Human Knowledge
RAG v2 without adjusting its corpus, preprocessing, sparse/dense logic, RRF constant, candidate
limit, queries, labels, or thresholds.

The frozen test contains 105 cases: 84 positives across 42 accepted families and two styles, four
merge-to-existing-variant controls, seven forbidden held-family controls, and ten zero-overlap
unrelated controls. It is wholly test-only and excluded from training, query rewriting, threshold
selection, retriever tuning, canonical truth, PostgreSQL ingestion, and production claims.

## Versioned artifacts

| Artifact | Identity |
|---|---|
| Query pack | `family-retrieval-query-pack-v1`, SHA-256 `26e244c04325f7909fb222b6cdd32ee2301253db17f0b8b97cf2f63ac4358733` |
| Owner decisions | `family-retrieval-owner-decisions-v1`, SHA-256 `d22b96bb16cd9cb9e19f4a4723a41b653da7b4961b5b588f6f636e1b37e1bad1` |
| Benchmark | `family-retrieval-holdout-v1`, SHA-256 `440246fb6a3b38f56fc25c1ec939d53d6cfc4457fed738aad561899325808afd` |
| Retriever | `human-knowledge-hybrid-v2`; 100 provisional variants + 42 review families |
| Dense representation | Deterministic `hashing-v1`, 192 dimensions; not a neural embedding |
| Fusion/evaluation | RRF `k=60`; K=5 |
| Raw result | `reports/family-retrieval-v1/evaluation.json` |
| Readable report | `reports/family-retrieval-v1/evaluation.md` |
| AI-eval | `docs/evidence/ai-evals/family-retrieval-holdout-v1.md` |

The evaluator validates the benchmark, manifest, every referenced input, and the frozen runtime
source hashes before scoring. Each case retrieves first and reveals its expected branch afterward.
The report validator derives expected ranks and error categories from candidate arrays, then
recomputes every numerator, denominator, metric, gate, and verdict. JSON and Markdown checks are
byte-deterministic, and invalid input cannot overwrite an existing report.

## Measured result

| Gate | Raw value | Result |
|---|---:|:---:|
| Positive Recall@5 `>=0.85` | `73/84 = 0.8690` | PASS |
| Positive Recall@1 `>=0.65` | `58/84 = 0.6905` | PASS |
| Positive MRR@5 `>=0.75` | `65.0/84 = 0.7738` | PASS |
| Lexical-variation Recall@5 `>=0.75` | `31/42 = 0.7381` | **FAIL** |
| Marketplace-noise Recall@5 `>=0.75` | `42/42 = 1.0000` | PASS |
| Family coverage@5 `>=0.90` | `42/42 = 1.0000` | PASS |
| Merge-control Recall@5 `=1.0` | `4/4 = 1.0000` | PASS |
| Forbidden family hits `=0` | `0` | PASS |
| Unrelated non-empty results `=0` | `0/10` | PASS |

Error accounting is exhaustive: 94 cases are `none`, ten are
`expected_identity_not_retrieved`, and one is `no_candidates`. All eleven errors are lexical-
variation positives. The result therefore supports a narrow conclusion: marketplace wrapper noise
and safety controls work on this bounded set, while name variation robustness misses its agreed
minimum. It does not support release-variant or production accuracy.

## Complete QA evidence

The final host suite passed **201/201**, covering unit, integration, API, UI DOM harness,
evaluation/reporting, frozen-data, and negative paths. The known local Starlette/AnyIO TestClient
deprecation warning remains non-failing and unrelated to T48.

The complete immutable-data chain reproduced successfully:

1. Synthetic fixture and 100-row Fandom pilot validation.
2. Pilot review, 53-family base queue, priority-one evidence/decision.
3. Five sequential priority-two research and owner-decision checkpoints.
4. Review-family registry (`42 new / 4 merge / 7 hold`) and 42-document runtime projection.
5. T48 query pack, owner decisions, benchmark, JSON evaluation, and Markdown report.

A fresh canonical fixture report retained all prior ranking/reliability results: Recall@25 and
Top-1 `1.0`, hard-negative accuracy and precision `1.0`, false-match rate `0.0`, and coverage
`0.8333`. The T47 tests retained 142 globally unique human-knowledge documents, all 42 exact family
names within Top-5, the BMW variant behavior, and Proton Saga as canonical `no_match` with family
debug evidence only.

Python compilation, JavaScript syntax, default and PostgreSQL-profile Compose parsing, whitespace,
and protected-file scope checks passed. The pre-T48 implementation baseline `b7f6ac1` through this
closure changes no canonical catalog/benchmark, calibration/policy, runtime human retriever/service,
migration, Compose, or PostgreSQL implementation file. All changed files remain inside the Product
Variant Resolver repository.

Targeted Ruff and isolated strict MyPy pass for the T48.4 evaluator, renderer, and tests. The whole
repository still has 143 Ruff 0.16.7 findings and 817 strict MyPy findings, primarily legacy import/
annotation style plus unavailable optional PostgreSQL/observability imports. These are explicit
maintenance debt and are not represented as T48 regressions or silently fixed during this bounded
QA task.

## Decision and next work

T48 is complete, but its quality verdict is FAIL. T49 is not permitted to begin, and the current
family source remains local/debug-only. Repeating v1 with a modified model would be tuning against a
known test. The next feature must specify a retrieval redesign and separate development evidence;
final quality judgment then requires a newly composed, owner-approved v2 holdout. PostgreSQL/
pgvector persistence and growth toward approximately 3,000 rows remain downstream of that PASS.
