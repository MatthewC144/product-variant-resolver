# Neural reranker architecture comparison v1 — public evidence

Date: 2026-09-25. Lite / Lean Industrial. Verdict: **valid shadow experiment; `winner: null`**.

## Question and experimental boundary

This experiment asks whether a local neural pointwise cross-encoder or a genuine candidate-set
listwise reranker improves the canonical resolver's unchanged RRF order for near-duplicate variants.
Every arm receives one byte-bound candidate set, so reranking is the only intended difference.

The evidence covers a 100-case synthetic/curated fixture benchmark backed by a 120-product fixture
catalog. It is not production marketplace evidence. Train/Dev/Test are casting-family disjoint at
58/21/21 cases. Test has 12 matched ranking targets, 4 ambiguous and 5 no-match cases; 4 of the
matched targets are hard negatives.

## Frozen architecture and lifecycle

- Baseline: canonical sparse+dense+structured retrieval and RRF, Top-25.
- Pointwise: Apache-2.0 `cross-encoder/ms-marco-MiniLM-L6-v2`, immutable revision
  `233902d25c440f23af6f7d6e94d2946bac0bee0a`, CPU float32, frozen weights.
- Listwise: 21→32 candidate encoder, one four-head/64-feedforward self-attention layer without
  positional embeddings, scalar head, masked listwise cross-entropy and Train-only normalization.
- Training: 36 eligible matched Train lists; Dev has 12 eligible lists and selects epoch only.
- Selection: Dev MRR@10 is 1.0 for epochs 1–11; strict improvement plus patience 10 retains epoch 1.
- Test: exactly 21 label-blind retrieval calls, 25 candidates per row, zero errors and no retry.

The raw artifact existed before Test labels were joined. It contains no expected/target/label,
accuracy/metric, eligibility or winner key. A second collection returns `unchanged`. After raw
publication, source/config/model/hyperparameter bytes remain frozen.

## Exact measured result

| Arm | Top-1 | MRR@10 | Hard-negative | Recall@10 | Recall@25 | Resolver p50/p95 |
|---|---:|---:|---:|---:|---:|---:|
| RRF | `12/12` | `12/12` | `4/4` | `12/12` | `12/12` | `1.009 / 1.398 ms` |
| Neural pointwise | `12/12` | `12/12` | `4/4` | `12/12` | `12/12` | `79.003 / 89.164 ms` |
| Neural listwise | `12/12` | `12/12` | `4/4` | `12/12` | `12/12` | `79.399 / 89.583 ms` |

Both declared failure categories contain six matched cases. All three arms are `6/6` Top-1 and
MRR@10 for `identifier_noise`; all are also `6/6` for `marketplace_noise`, including `4/4` matched
hard negatives. Every one of the 12 pointwise and 12 listwise paired transitions is
rank 1 → rank 1 (`unchanged`). Listwise context therefore changed no measured target rank.

Each neural arm passes hard-negative, MRR, Recall@25, latency and zero-error gates. Each fails only
the required Top-1 absolute gain gate: actual `0.00`, threshold `0.05`. The deterministic selection
is `winner: null`; RRF remains the default.

## Immutable evidence

| Artifact | SHA-256 |
|---|---|
| MiniLM local manifest | `32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8` |
| Listwise checkpoint | `9386c0593ec07ad2b9eb0f6daa613b66f7b117e0e6c5a33be2e8705dbe18aead` |
| Label-blind Test raw | `948582264e67ad6d686a4409a41100149118d12b6e4548bbdc1265d778756884` |
| Comparison JSON | `f0493fc5d7b30b5e57ee382cf14e06e4fddbcebc62228b9f4b5a0dcec45b3dd2` |
| Comparison Markdown | `0a90e7803db1497584ef2ee2e6b78cd47e95f750db3b9697b447a7016a7ae0fb` |
| Reranker comparison SVG | `028f88117af4962d4d1d25a6c765e23b9143d84cf280641f6b6f78d4d54d87c6` |
| Accuracy/latency SVG | `3a3156f3ba9f866c68afd435a1054ead2b29543c76cc452439df182a5f0dfe7c` |
| Report manifest | `3d21f0eef71f19a207f3459843eaad6abb5708c8218fb5c540698e1a372e271b` |

The committed model cache intentionally excludes the 88 MB pretrained MiniLM weights. Its manifest,
revision and allowed-file hashes make the local snapshot reproducible; formal data contains the
small project-trained listwise safetensors checkpoint and both selection manifests.

## Interpretation and release boundary

The null result is not a claim that neural reranking is generally ineffective. RRF already ranks all
12 fixture targets first, leaving no upside for this Test. One case changes Top-1 by `0.0833`, so the
sample is too small for production or statistical claims. Raw neural scores are ranking scores, not
calibrated match probabilities and not comparable across architectures.

The experiment changes no FastAPI behavior, runtime reranker flag, calibration, threshold,
PostgreSQL data, canonical identity, Human Knowledge RAG, review-family state or release promotion.
A new non-ceiling benchmark and separately frozen v2 protocol would be required before another
neural comparison; v1 remains immutable negative evidence.
