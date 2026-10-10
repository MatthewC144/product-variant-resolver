# Domain ranker v2 remediation — Tasks

Date: 2026-10-10. Mode: Lite / Lean Industrial. Status: **DRV2-T0–T5 complete; T6+ not authorized**.

- [x] **DRV2-T0 — Preserve the v1 negative result and draft the remediation hypothesis.** Record
  observed failures, distinguish hypotheses from proven causes, retain all holdout boundaries and
  define the next Owner decisions. _(→DRV2-R1, R2, R10, R12)_
- [x] **DRV2-T1 — Materialize v2 governance.** Bind the approved frozen source, owner-authored query
  protocol, exact permitted uses, rights/authority, publication scope and all v1/legacy denylist
  hashes. _(→DRV2-R1, R2, R11)_
- [x] **DRV2-T2 — Build family/evidence-safe v2 partitions.** Produce at least 120/30/30 train,
  validation and selection rows from at least 180 new queries. _(→DRV2-R3, R6)_
- [x] **DRV2-T3 — Freeze generic candidate pools and execute latency readiness.** Bind the environment and
  query-only Top-25 pools; stop before training if generic p95 exceeds 200 ms. _(→DRV2-R7, R8)_
- [x] **DRV2-T3R — Repair generic CPU inference latency without changing ranking semantics.** Freeze
  one implementation approach, prove generic-score/order equivalence and rerun the identical
  validation benchmark before T4. _(→DRV2-R8)_
- [x] **DRV2-T4 — Mine exact-release pairwise triples.** Require at least 60 train queries with two
  defensible same-casting negatives; hold ambiguous siblings. _(→DRV2-R4)_
- [x] **DRV2-T5 — Train the single fixed pairwise recipe.** Use two seeds, validation-only early
  stopping and safetensors-only release artifacts. _(→DRV2-R5, R6)_
- [ ] **DRV2-T6 — Execute untouched selection once.** Apply frozen metrics, gates and tie rules and
  emit a selected checkpoint hash or `winner: null`. _(→DRV2-R9, R10)_
- [ ] **DRV2-T7 — Complete Lite QA and evidence.** Verify integrity, isolation, aggregate-only
  publication, unchanged runtime and claim boundaries. _(→DRV2-R11, R12)_

## Current Gate

T1 completed under the owner's next-step instruction after the five-item handoff. Governance SHA-256
is `5b981e79df16510210b529a299932dc52c54b3b776808f792433f002eb7d03f8`. The owner's following
next-step instruction opens T2 only. This decision does not authorize reuse of the 53/20 holdouts,
52 no-match rows or T2 selection errors, and it does not open T3 scoring. T2 is now frozen at query
pack content SHA-256 `149d7d867b9e270ffb805906aec64685d6823f11efcd68a59e9e74ba60134e6f`
with 120/30/30 rows and zero cross-partition family overlap. T3 still requires a separate Gate.
The owner's latest next-step instruction opened T3 only. T3 froze 180 query-only Top-25 pools with
zero retrieval misses and zero target injections, but generic CPU p95 was `217.699834 ms`, above the
fixed `200 ms` ceiling. T3 is therefore execution-complete with a failed readiness result. T3R needs
a separate Owner Gate; the owner's latest next-step instruction opened T3R only. Float32 ONNX
preserved all 180 Top-25 orderings with maximum logit delta `1.4781951904296875e-05` and reduced
validation CPU p95 to `103.654042 ms`, so the latency Gate passes. The owner's latest next-step
instruction opened T4 only. Evidence-gated mining admitted 112/120 train queries and produced 332
triples; 27 sibling records remain held, validation/selection label reads are zero and no model was
trained. The owner's latest next-step instruction opens T5 only. Its fixed RankNet-style logistic
recipe, two seeds, validation-only early stopping and safetensors release contract are now frozen
before training. The completed run selected seed-17 epoch 2 and seed-29 epoch 3, both at validation
MRR@10 `0.95`, and released two strictly validated float16 safetensors files. Selection reads and
model-selection runs remain zero. T6 selection, calibration, final evaluation and runtime remain
unauthorized.
