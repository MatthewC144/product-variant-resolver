# Domain ranker and selective prediction development v1 — Tasks

Date: 2026-10-09. Mode: Lite / Lean Industrial. Status: **DRSP-T1 complete; T2+ not authorized**.

Tasks are ordered Gates. A checked task may unlock only the next listed task; it never authorizes
runtime activation, public weights or final evaluation.

- [x] **DRSP-T1 — Materialize the training-use and authority Gate.** Bind permitted source hashes,
  uses, fields, authority wording, retention/publication scope and permanent 53/20 denylist. Reject
  unresolved third-party rights instead of inferring permission. _(→DRSP-R1–R3, R14–R16)_
- [ ] **DRSP-T2 — Freeze family/evidence-safe development partitions and candidate pools.** Produce
  non-reversible split/candidate manifests, prove zero leakage and report retrieval misses without
  injecting targets. _(→DRSP-R2–R4)_
- [ ] **DRSP-T3 — Implement deterministic one-shot hard-negative mining.** Mine only train rows,
  preserve near-duplicate categories, hold ambiguous siblings and publish safe aggregate taxonomy.
  _(→DRSP-R5–R6, R14)_
- [ ] **DRSP-T4 — Fine-tune the pinned domain MiniLM.** Use one frozen binary objective, two seeds,
  fixed early stopping and local safetensors/checkpoint lineage. _(→DRSP-R7, R15)_
- [ ] **DRSP-T5 — Compare and freeze the ranker.** Evaluate generic/domain Pointwise on identical
  selection pools, apply quality/latency/stability gates and publish either a selected ranker or
  `winner: null`. _(→DRSP-R8–R9)_
- [ ] **DRSP-T6 — Build disjoint calibration fit/selection artifacts.** Score only admitted
  calibration rows with the frozen ranker and compare predeclared calibrators on identical scores.
  _(→DRSP-R9–R11)_
- [ ] **DRSP-T7 — Select the development-only three-state policy.** Produce reliability,
  precision/risk-coverage and AURC evidence; emit a shortfall if no frozen operating point passes.
  _(→DRSP-R11–R13, R16)_
- [ ] **DRSP-T8 — Add integrity, privacy and regression tests.** Cover authorization, denylist,
  leakage, deterministic mining/training, unsafe weights, artifact tampering, aggregate-only output
  and unchanged FastAPI defaults. _(→DRSP-R1–R16)_
- [ ] **DRSP-T9 — Execute one development run and complete Lean QA.** Run only after T1–T8 pass;
  publish aggregate development evidence and explicitly report zero final/holdout reads.
  _(→DRSP-R1–R16)_
- [ ] **DRSP-T10 — Curate the decision and project evidence.** Record the result or negative result,
  technical trade-offs, model/data lineage, limitations and the separate prerequisites for a fresh
  final test. _(→DRSP-R8, R13–R16)_

## Owner Gates before T1 can pass

1. **Resolved for local-only development:** owner selected Path B. The 100 positive development rows
   may be used for local partitioning, mining, fine-tuning and selection. This is recorded as owner
   attestation, not independently verified third-party rights; public weights remain prohibited.
2. **Resolved:** the existing 52 development no-match rows may be reused only for calibration fit and
   threshold selection. They may not train the ranker; the 20-row holdout remains permanently excluded.
3. Choose the source for new ranker/calibration rows when existing permissions are insufficient:
   owner-authored/synthetic (safer, weaker external-validity claim) or a newly rights-cleared source.
4. Approve or revise the proposed ranker, calibration and selective-prediction acceptance gates
   before any result is visible.
5. **Resolved:** checkpoint scope is local-only; Git may contain only manifest/hash/count/limitations
   and aggregate evidence.
6. **Resolved:** this milestone is development-only. Fresh final evaluation and runtime promotion
   require separate future Gates.

Items 3–4 remain future decisions for T2+; completing T1 does not imply their approval.

## G1 acceptance

Requirements, design and tasks are approved together; every adaptive phase is separated; legacy
holdouts are permanently denied; public/private artifact contracts are explicit; metrics and stop
conditions are frozen; and unresolved source rights remain a blocking Gate rather than a warning.
