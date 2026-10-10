# Domain ranker training v1 — T4 AI evaluation evidence

Date: 2026-10-09. Scope: DRSP-T4 only. Verdict: **PASS for controlled training and checkpoint
packaging; ranker quality winner not evaluated**.

## Dataset and leakage boundary

- Input: released T3 package SHA-256
  `89bc430289c36e75c6302e7aa4ecca1889f32df95e5199f61aba1f676b18022a`.
- Training: 345 positive/negative pairs, projected to 690 balanced binary examples from 69 queries.
- Early stopping only: 30 frozen ranker-selection queries with identical T2 Top-25 pools.
- Positive test reads/scores: 0; negative holdout reads/scores: 0; no-match development reads/scores:
  0; calibration/final/runtime actions: 0.
- Authority remains frozen-community-catalog-relative and
  `owner_attested_not_independently_verified`, not manufacturer/global truth.

## Fixed recipe and results

Binary BCE-with-logits, seeds 17/29, max four epochs, patience two, batch 16, learning rate `2e-5`,
weight decay `0.01`, warmup `0.1`, max length 128 and gradient clipping `1.0`. Both seeds selected
epoch 1 at selection MRR@10 `0.86111111` and stopped at epoch 3. The later training losses improved
while selection MRR declined, so early stopping prevented the lower-loss checkpoints from replacing
the earlier ranking checkpoint.

This result does not satisfy or fail the DRSP ranker-qualification rubric by itself. T4 did not run
the generic baseline on the comparison protocol, compute exact Top-1/casting Top-1/hard-negative
accuracy/latency, or declare a winner. Those are T5 measurements.

## Artifact safety and reproducibility

- Package SHA-256:
  `1cc26cc8aea072d02cb5fd25909b0adfcdbdfd2a7f642433945cf00211b002e1`.
- Seed 17 checkpoint SHA-256:
  `652f1e900bfeefd1536603e2d7e3b9c783df7b93273eb0a83a3bb0dce4360417`.
- Seed 29 checkpoint SHA-256:
  `315df109e64798108cb06fb249cb43f85f625e8224f34b51559b8d4c74cecb2d`.
- Training code commit: `14bcf2866becc4b1215155010157cdf5f4f63ee2`.
- Two float16 safetensors files, each 45,439,178 bytes; no pickle or optimizer state.
- Two consecutive clean rebuilds produced the same checkpoint and package hashes.
- Exact 14-file recursive allowlist, text scan, license/NOTICE/model card, full lineage and offline
  load with `trust_remote_code=false` all pass.

## Claim boundary

Permitted claim: the project now demonstrates governed domain cross-encoder fine-tuning with
two-seed stability, deterministic early stopping and supply-chain-aware checkpoint packaging.

Not permitted: the fine-tuned model is better than the generic model, production-ready, calibrated,
manufacturer-certified, final-test validated or active in FastAPI.
