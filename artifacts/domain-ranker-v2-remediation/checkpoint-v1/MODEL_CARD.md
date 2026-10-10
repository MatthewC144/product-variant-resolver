# Product Variant Resolver pairwise domain MiniLM checkpoints v2

These checkpoints fine-tune `cross-encoder/ms-marco-MiniLM-L6-v2` revision `233902d25c440f23af6f7d6e94d2946bac0bee0a` on 332
community-catalog-relative same-casting exact-release triples.

## Fixed training recipe

- Objective: RankNet-style pairwise logistic loss, `softplus(-(positive-negative))`.
- Seeds: 17 and 29; learning rate `1e-5`; at most four epochs.
- Early stopping: 30 frozen validation queries, MRR@10, patience two.
- Published weights: float16 safetensors only; no optimizer or pickle state.

- Seed 17: selected epoch 2, stop epoch 4, validation MRR@10 0.95000000.
- Seed 29: selected epoch 3, stop epoch 4, validation MRR@10 0.95000000.

## Intended use and limitations

These are experimental offline ranking artifacts for the separately gated DRV2-T6 comparison.
T5 does not read the selection partition, choose a winner, calibrate confidence, run a final test,
activate runtime or expose an endpoint. Labels are relative to a frozen community snapshot and are
not manufacturer-certified or global truth. Source and redistribution rights are owner-attested,
not independently verified; color and edition remain incomplete.
