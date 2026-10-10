# Product Variant Resolver domain MiniLM checkpoints v1

These two checkpoints fine-tune `cross-encoder/ms-marco-MiniLM-L6-v2` revision `233902d25c440f23af6f7d6e94d2946bac0bee0a` on the
released DRSP-T3 binary hard-negative pairs. They are experimental ranking artifacts for the
frozen Hot Wheels community-catalog-relative resolver task.

## Training

- Objective: binary Pointwise relevance with BCE-with-logits.
- Seeds: 17 and 29; fixed recipe; train data only from the 345 T3 pairs.
- Early stopping: frozen 30-query ranker-selection MRR@10; no final or calibration data.
- Published weights: float16 safetensors only; no optimizer state or pickle payload.

- Seed 17: selected epoch 1, early-stop epoch 3, selection MRR@10 0.86111111.
- Seed 29: selected epoch 1, early-stop epoch 3, selection MRR@10 0.86111111.

## Intended use and limitations

Use only for offline candidate reranking and the separately gated DRSP-T5 comparison. These
weights are not a product identifier by themselves, are not manufacturer-certified, and do not
establish global truth. The data and redistribution permissions are owner-attested and were not
independently verified. Color and edition remain incomplete. T4 does not select a winner, calibrate
confidence, evaluate a final holdout, activate runtime, or expose an inference endpoint.
