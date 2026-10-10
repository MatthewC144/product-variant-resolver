# Domain ranker v2 pairwise training — AI-eval rubric

Date: 2026-10-10. Scope: DRV2-T5. Verdict: **TRAINING AND CHECKPOINT RELEASE PASS; MODEL IMPROVEMENT NOT YET EVALUATED**.

| Rubric | Evidence | Result |
|---|---|---|
| Preregistration | Recipe/code commit `44eee2e` exists before training output | PASS |
| Frozen input | 332 T4 triples from 112 train queries; exact parent hashes enforced | PASS |
| Single hypothesis | RankNet-style `softplus(-(positive-negative))`; no objective search | PASS |
| Validation isolation | 30 validation pools only; selection rows read/scored 0 | PASS |
| Two-seed stability | Seed 17 epoch 2 and seed 29 epoch 3 both reach MRR@10 `0.95` | PASS |
| Serialization | Two float16 safetensors; strict tensor schema and offline load | PASS |
| Package safety | 14-file allowlist; no symlinks, pickle or optimizer state | PASS |
| Publication privacy | Aggregate history only; no row-level query/triple/prediction data | PASS |
| Runtime boundary | calibration/final evaluation/runtime activations all 0 | PASS |

Pairwise loss decreased for both seeds, but decreasing training loss is not treated as a quality
claim. Validation MRR selected the earliest best epoch under the frozen tie rule. The checkpoints
are candidates for DRV2-T6, not selected production models.

Checkpoint SHA-256 values are
`5a4f2ea21b93a864f1e1ddb54523f68a0ae2766db555535c0f35721588b6e297` (seed 17) and
`83db9ab75c1c431ce2c6f3e4c717bae821c187a060f0864e45204ee8a4056e99` (seed 29). Package SHA-256 is
`28977b447a3ec7b7fa970d7c5eec8ce3b0a2c5f33b4c50c3dbd6dfca7dbb7663`.

T5 does not show that either checkpoint improves exact-release ranking versus generic. Only a
separately authorized, one-shot T6 comparison on the untouched selection partition may make that
determination. Calibration, fresh final evaluation and runtime activation remain downstream and
conditional on a non-null T6 winner.
