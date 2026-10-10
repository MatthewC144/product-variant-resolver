# Domain ranker selection v1 — T5 AI evaluation evidence

Date: 2026-10-09. Scope: DRSP-T5 only. Verdict: **faithful evaluation PASS; domain-ranker gate FAIL;
`winner: null`**.

## Question and frozen comparison

The experiment asks whether the T4 domain-adapted Pointwise cross-encoder improves over the pinned
generic MiniLM on the exact same catalog-relative candidate sets. It does not ask whether training
loss falls, whether the checkpoints can be loaded, or whether a favorable subset can be found after
inspection. The comparison code was committed as `a23b1b27073ea16c93c1eda9d814824638ccee58`
before scores were produced. It binds the T2 pool file, T4 package, generic weights, both checkpoint
weights and the preregistered quality/latency gates by SHA-256.

All three arms re-score 30 frozen selection queries with 25 candidates each. Ties use score then UUID;
same-family negatives require a strict score win. CPU latency contains three warm-ups and 90 measured
query batches per arm. Row-level ranks and latency samples remain private; the public artifact is
aggregate-only.

## Results

| Metric | Generic | Domain seed 17 | Domain seed 29 |
|---|---:|---:|---:|
| Exact Top-1 | `24/30` (80.00%) | `23/30` (76.67%) | `23/30` (76.67%) |
| Casting Top-1 | `30/30` (100%) | `30/30` (100%) | `30/30` (100%) |
| MRR@10 | `0.87777778` | `0.86111111` | `0.86111111` |
| Recall@25 | `30/30` | `30/30` | `30/30` |
| Same-family accuracy | `41/52` (78.85%) | `40/52` (76.92%) | `40/52` (76.92%) |
| CPU p95 | `243.924917 ms` | `243.6395 ms` | `244.865875 ms` |

The two seeds agree, but in the wrong direction: each loses one exact case, `0.01666667` MRR and one
same-family comparison. They preserve casting and retrieval recall, and their relative latency stays
within 1.25× of generic, but all arms exceed the absolute 200 ms budget on this CPU. Neither domain
seed meets the exact, MRR, same-family, absolute-latency or positive-direction gate.

## Decision and claim boundary

The frozen result is `winner: null`; selected checkpoint SHA-256 is null. T6 calibration is blocked
because a failed ranker cannot be converted into a winner by calibrating its score. The checkpoints
remain legitimate, reproducible evidence that the project implemented hard-negative mining,
fine-tuning, safetensors packaging and controlled evaluation. They are not evidence of improved
quality, production readiness or deployability.

Permitted claim: the project completed a governed domain adaptation experiment and rejected the
fine-tuned models when preregistered selection gates failed.

Not permitted: domain fine-tuning improved ranking; a domain checkpoint is selected; scores are
calibrated probabilities; manufacturer/global truth was established; final evaluation ran; runtime
behavior changed.

## Integrity and isolation

- Result content SHA-256:
  `d9665b151c4c3263afd8e24345024985904f1a407d93ce6c9173ed37d8444e2b`.
- Result file SHA-256:
  `219789db3f1e6f7e3e114656d165ca3ebe733225139e294787dc64beaa3e25c3`.
- Authorization file SHA-256:
  `09c8a38be0b9e5208f750fc9966a9fbbe20c074b37d1a419b8c8237923168fa7`.
- Positive-test rows read/scored: `0`; negative holdout: `0`; no-match development: `0`.
- Calibration fits: `0`; fresh-final evaluations: `0`; runtime activations: `0`.
- Public row-level records: `0`; local diagnostics are Git-ignored and mode `0600`.
