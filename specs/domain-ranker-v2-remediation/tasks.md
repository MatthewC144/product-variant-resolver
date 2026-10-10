# Domain ranker v2 remediation — Tasks

Date: 2026-10-09. Mode: Lite / Lean Industrial. Status: **Only DRV2-T0 complete; T1+ require Owner
Gate**.

- [x] **DRV2-T0 — Preserve the v1 negative result and draft the remediation hypothesis.** Record
  observed failures, distinguish hypotheses from proven causes, retain all holdout boundaries and
  define the next Owner decisions. _(→DRV2-R1, R2, R10, R12)_
- [ ] **DRV2-T1 — Materialize v2 governance.** Bind an approved new dataset, exact permitted uses,
  rights/authority, publication scope and all v1/legacy denylist hashes. _(→DRV2-R1, R2, R11)_
- [ ] **DRV2-T2 — Build family/evidence-safe v2 partitions.** Produce at least 120/30/30 train,
  validation and selection rows from at least 180 new queries. _(→DRV2-R3, R6)_
- [ ] **DRV2-T3 — Freeze latency-ready generic candidate pools.** Bind the environment and
  query-only Top-25 pools; stop before training if generic p95 exceeds 200 ms. _(→DRV2-R7, R8)_
- [ ] **DRV2-T4 — Mine exact-release pairwise triples.** Require at least 60 train queries with two
  defensible same-casting negatives; hold ambiguous siblings. _(→DRV2-R4)_
- [ ] **DRV2-T5 — Train the single fixed pairwise recipe.** Use two seeds, validation-only early
  stopping and safetensors-only release artifacts. _(→DRV2-R5, R6)_
- [ ] **DRV2-T6 — Execute untouched selection once.** Apply frozen metrics, gates and tie rules and
  emit a selected checkpoint hash or `winner: null`. _(→DRV2-R9, R10)_
- [ ] **DRV2-T7 — Complete Lite QA and evidence.** Verify integrity, isolation, aggregate-only
  publication, unchanged runtime and claim boundaries. _(→DRV2-R11, R12)_

## Current Gate

No T1+ action is authorized. The owner must first approve the data target/source, 120/30/30 split,
single pairwise objective, preregistered gates and publication boundary listed in `requirements.md`.
This draft does not authorize reuse of the 53/20 holdouts, 52 no-match rows or T2 selection errors.
