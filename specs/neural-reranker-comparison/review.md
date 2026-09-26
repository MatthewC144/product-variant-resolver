# QA review — Neural reranker architecture comparison v1

Date: 2026-09-25. Verdict: **experiment integrity PASS; neural promotion FAIL; runtime unchanged**.

## Requirements coverage

| Requirement | Evidence | Result |
|---|---|---|
| NRC-R1 | All 100 benchmark cases and every candidate bind to the committed 120-product `fixture-v1` canonical catalog; Human Knowledge/release evidence is absent | PASS |
| NRC-R2 | Exact 100/58/21/21 counts, status/hard-negative counts, 14 families and family-disjoint splits validate | PASS |
| NRC-R3 | Train/Dev and Test use one frozen canonical Top-25 pool per case; 21 Test rows made exactly 21 retrieval calls | PASS |
| NRC-R4 | Report contains exactly `rrf`, `neural_pointwise`, and `neural_listwise` | PASS |
| NRC-R5 | Frozen MiniLM scores independent pairs; real batch reversal maps scores within `1e-6` | PASS |
| NRC-R6 | The 21→32 attention head receives complete candidate sets; real permutation and padding preflights pass | PASS |
| NRC-R7 | Feature schema is allowlisted; IDs, split, labels, row order and private/Human Knowledge outcomes are excluded from predictive features | PASS |
| NRC-R8 | 36 eligible Train lists fit weights; 12 eligible Dev lists select earliest epoch 1; Test labels are joined only after immutable raw collection | PASS |
| NRC-R9 | Frozen pools had zero matched-target retrieval misses; Recall@10/25 remains explicit and identical for all arms | PASS |
| NRC-R10 | Model/revision/license, 33 dependency pins, CPU float32, architecture, seed, normalizer, training history and artifact hashes are recorded | PASS |
| NRC-R11 | Exact Top-1, MRR@10, hard-negative, Recall@10/25, warmed latency, numerators/denominators, categories and paired transitions are published | PASS |
| NRC-R12 | Both neural arms pass safety/latency/error gates but fail required Top-1 gain `0.00 >= 0.05` | FAIL for recommendation, correct measured result |
| NRC-R13 | Selector publishes `winner: null`; RRF remains default and no Test retuning occurs | PASS |
| NRC-R14 | Six-phase CLI, exclusive writes, canonical JSON, manifests, repeat `unchanged`, full `valid` check and tamper tests pass | PASS |
| NRC-R15 | Scored cases expose shared candidates, all three ranks/scores, timings, transitions, evidence scope and non-calibrated score semantics | PASS |
| NRC-R16 | FastAPI, calibration, thresholds, PostgreSQL, canonical data, Dual RAG and review/release state are unchanged | PASS |
| NRC-R17 | JSON/Markdown/two SVGs, README table, denominators, hardware, limitations and honest null result are published | PASS |

## Measured result

RRF is already perfect on the 12 matched fixture Test cases: Top-1 `12/12`, MRR@10 `12/12`,
Recall@10/25 `12/12`, and matched hard-negative accuracy `4/4`. Pointwise and listwise produce the
same exact ranking metrics and keep every matched target at rank 1. Their absolute Top-1 gains are
therefore `0.00`, below the predeclared `0.05` minimum.

Latency and reliability do not cause the rejection. Pointwise/listwise resolver p95 values are
`89.164 ms` and `89.583 ms`, below the `1,500 ms` budget; collection errors are zero. Both arms fail
only the value gate. Selecting either arm because it is neural would add approximately 88 ms p95
without changing a measured target rank.

The result is bounded. Twelve matched synthetic/curated fixture cases do not prove production
accuracy, and a baseline ceiling prevents this version from measuring upside. It does prove that
the architecture comparison, leakage boundaries, one-time Test lifecycle, deterministic null branch
and negative-result reporting work as designed.

## QA and reproducibility

The immutable report JSON SHA-256 is
`f0493fc5d7b30b5e57ee382cf14e06e4fddbcebc62228b9f4b5a0dcec45b3dd2`; the raw Test SHA-256 is
`948582264e67ad6d686a4409a41100149118d12b6e4548bbdc1265d778756884`. Report/check commands return
`unchanged` and `valid`. Measured-artifact regressions bind report/raw hashes, exact metrics/gates,
paired rank transitions, candidate equality and label blindness.

Focused neural/evaluation, related integration and full-suite results are recorded in NRC-T10 task
evidence and the Project Log. Targeted Ruff format/check, strict MyPy, compileall, installed CLI,
artifact/hash/README consistency and `git diff --check` pass. The remaining suite warning is the
existing Starlette/AnyIO deprecation warning.

## Release boundary and carry-forward

This review authorizes publication of the shadow result only. It does not authorize a neural runtime
arm, a new confidence threshold, API changes, Dual RAG integration, PostgreSQL changes, canonical or
Human Knowledge mutation, release promotion, or claims about real marketplace coverage. RRF remains
the runtime default.

A future experiment would require a separately versioned benchmark with non-ceiling matched cases,
new pre-Test protocol and new model selection. V1 must not be retuned or overwritten after observing
this null result.
