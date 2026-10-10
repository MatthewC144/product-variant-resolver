# Domain ranker v2 selection — closure evidence

Date: 2026-10-10. Scope: DRV2-T1–T7. Verdict: **experiment reproducible; model qualification
failed; `winner: null`; runtime unchanged**.

## What was evaluated

V2 authored 180 new catalog-present queries from 180 distinct casting families and froze them into
120 train, 30 validation and 30 untouched selection rows. Query-supported exact-release conflicts
produced 332 pairwise triples across 112 train queries. One fixed RankNet-style MiniLM recipe was
trained with seeds 17 and 29; validation selected epochs 2 and 3, both at MRR@10 `0.95`.

Selection metrics, gates, ONNX equivalence and tie rules were committed as `5e67fbb` before the
single 30-query selection evaluation. Generic and both domain arms used the same float32 ONNX CPU
runtime for latency. Each domain export also had to preserve its PyTorch Top-25 ordering before its
quality result could be accepted.

## Frozen result

| Arm | Exact Top-1 | Casting Top-1 | MRR@10 | Same-family | Recall@25 | CPU p95 |
|---|---:|---:|---:|---:|---:|---:|
| Generic | 23/30 | 30/30 | 0.8778 | 79/87 | 30/30 | 106.127 ms |
| Seed 17 | 24/30 | 30/30 | 0.8944 | 80/87 | 30/30 | 121.251 ms |
| Seed 29 | 23/30 | 30/30 | 0.8722 | 78/87 | 30/30 | 114.842 ms |

Seed 17 improved exact Top-1 by one case, MRR@10 by `0.0167`, and same-family accuracy by
`0.0115`. These are below the frozen +3 cases, `+0.02`, and `+0.10` requirements. Seed 29 did not
improve exact Top-1 and regressed MRR and same-family accuracy. The two-seed direction check also
failed. Both arms passed casting, Recall@25, absolute/relative latency, and complete ONNX ordering
equivalence; the rejection is therefore a quality decision rather than an export or speed failure.

## Integrity and release boundary

| Evidence | Value |
|---|---|
| T5 package SHA-256 | `28977b447a3ec7b7fa970d7c5eec8ce3b0a2c5f33b4c50c3dbd6dfca7dbb7663` |
| T6 authorization SHA-256 | `c43a161921d93a8804c8fa79287110e2b1dad55b5c87ada766ed6ec4ef5cc5c7` |
| T6 result SHA-256 | `2f4a32fbb0383bcd934af48734d6e60ab6603bc03093a084d5cdb552194dbefc` |
| Seed 17 ONNX max logit delta / order | `1.1921e-05`; 30/30 identical |
| Seed 29 ONNX max logit delta / order | `1.0490e-05`; 30/30 identical |

Public artifacts contain only authorization, hashes, aggregate metrics and gate outcomes. Private
row diagnostics and two 90,978,308-byte ONNX graphs remain Git-ignored and mode `0600`. FastAPI,
service wiring and default settings do not import either v2 checkpoint: offline mode,
`heuristic-v1`, and `reranker_enabled=false` remain the defaults. Calibration fits, final
evaluations and runtime activations are all zero.

T1–T7 focused coverage is 44 passing tests; adding config and FastAPI regressions yields 70 passing
tests. Ruff, target-local strict MyPy, the T6 CLI integrity replay and `git diff --check` pass. A
repository-wide smoke run was stopped at 102 passes and 13 failures; all 13 are the pre-existing
T49.3 experimental human-storage API initialization failures caused by its stale v4 protocol binding,
not by the v2 ranker or default API path.

## Portfolio interpretation

The defensible claim is that the project implements governed hard-negative mining, domain
fine-tuning, two-seed validation, safe checkpoint packaging, equivalent ONNX inference, and a
pre-registered one-shot model-selection Gate. It must not claim that domain fine-tuning improved
the resolver, that a v2 checkpoint is deployed, or that the synthetic catalog-derived selection is
representative production traffic. Rejecting both checkpoints is the intended behavior when
measured gains are smaller than the precommitted product threshold.
