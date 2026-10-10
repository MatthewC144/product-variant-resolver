# Domain ranker and selective prediction development v1 — Tasks

Date: 2026-10-09. Mode: Lite / Lean Industrial. Status: **DRSP-T1 through T5 complete with `winner: null`; T6 blocked and not authorized**.

Tasks are ordered Gates. A checked task may unlock only the next listed task; it never authorizes
an unchecked downstream task. T1A by itself grants only future publication eligibility: it does not mark a
pair package or checkpoint as released, authorize final evaluation, or activate runtime.

- [x] **DRSP-T1 — Materialize the training-use and authority Gate.** Bind permitted source hashes,
  uses, fields, authority wording, retention/publication scope and permanent 53/20 denylist. Reject
  unresolved third-party rights instead of inferring permission. _(→DRSP-R1–R3, R14–R16)_
- [x] **DRSP-T1A — Materialize the publication amendment and effective governance v2.** Preserve
  the frozen T1 artifacts; authorize future release-gated row-level hard-negative pairs and actual
  safetensors weights, and separate future publicability from final execution/runtime activation.
  _(→DRSP-R14–R16)_
- [x] **DRSP-T2 — Freeze family/evidence-safe development partitions and candidate pools.** Produce
  non-reversible split/candidate manifests, prove zero leakage and report retrieval misses without
  injecting targets. _(→DRSP-R2–R4)_
- [x] **DRSP-T3 — Implement deterministic one-shot hard-negative mining.** Mine only train rows,
  preserve near-duplicate categories, hold ambiguous siblings and produce an allowlisted, scanned,
  versioned public pair package only after its release Gate passes.
  _(→DRSP-R5–R6, R14)_
- [x] **DRSP-T4 — Fine-tune the pinned domain MiniLM.** Use one frozen binary objective, two seeds,
  fixed early stopping and safetensors/checkpoint lineage; publish actual weights only after the
  model-package license/privacy/reproducibility Gate passes. _(→DRSP-R7, R15)_
- [x] **DRSP-T5 — Compare and freeze the ranker.** Evaluate generic/domain Pointwise on identical
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

## Owner Gates recorded by T1 and T1A

1. **Resolved for development:** owner selected Path B. The 100 positive development rows may be
   used for partitioning, mining, fine-tuning and selection. This remains owner attestation, not
   independently verified third-party rights. T1A permits only release-gated minimized pair and
   safetensors packages; the hash-bound T3 pairs and T4 checkpoints have now passed those Gates.
2. **Resolved:** the existing 52 development no-match rows may be reused only for calibration fit and
   threshold selection. They may not train the ranker; the 20-row holdout remains permanently excluded.
3. Choose the source for new ranker/calibration rows when existing permissions are insufficient:
   owner-authored/synthetic (safer, weaker external-validity claim) or a newly rights-cleared source.
4. Approve or revise the proposed ranker, calibration and selective-prediction acceptance gates
   before any result is visible.
5. **Resolved by T1A amendment:** an actual safetensors checkpoint may be Git-tracked or released
   after the model-package Gate passes; optimizer state, pickle payloads, caches and scratch remain
   private. Large weights must use Git LFS or a release asset.
6. **Resolved by T1A amendment:** fresh-final aggregate reports and runtime code/config/model
   manifests may be public in the future. Final execution and runtime activation still require
   separate checksum-bound Owner Gates; row-level final data and a public endpoint remain
   unauthorized.
7. **Resolved for T2 only:** freeze the 100 admitted positive development rows into a deterministic
   70/30 family/evidence-safe split and query-only Top-25 pools. The resulting public artifacts are
   aggregate-only; private row-level membership and scores remain Git-ignored. This Gate does not
   authorize mining, training, model selection, calibration, final evaluation or runtime changes.
8. **Resolved for T3 only:** execute one deterministic pass over the 70 training rows and frozen T2
   pools, then release only the scanned five-file package whose pair/package hashes are
   `50f88e73889b31e8f314e93b2cca9e4871934662b5218c6659a72fe06c0ca2ba` and
   `89bc430289c36e75c6302e7aa4ecca1889f32df95e5199f61aba1f676b18022a`.
   This Gate discloses training membership for those pairs but authorizes no model training,
   checkpoint, calibration, final evaluation or runtime action.
9. **Resolved for T4 only:** the owner's next-step instruction after the explicit T4 handoff permits
   the frozen two-seed binary recipe, selection-only early stopping, and publication of the exact
   safetensors package only if its release Gate passes. It does not authorize T5 winner selection,
   calibration, final evaluation or runtime activation.
10. **Resolved for T5 only:** the owner's next-step instruction after the explicit T5 handoff permits
   one generic-versus-two-domain comparison on the frozen 30-query T2 selection pools, public
   aggregate metrics and either one frozen winner or `winner: null`. The Gate preserves the 53
   positive test rows, 20 negative holdout rows and 52 no-match development rows at zero reads and
   scores. It does not authorize calibration, final evaluation or runtime activation.

T4 released the exact package SHA-256
`1cc26cc8aea072d02cb5fd25909b0adfcdbdfd2a7f642433945cf00211b002e1`; both seeds selected epoch 1
at selection MRR@10 `0.86111111`. This is early-stopping evidence only, not a T5 winner decision.

T5 result SHA-256 is `d9665b151c4c3263afd8e24345024985904f1a407d93ce6c9173ed37d8444e2b`.
Both domain seeds regressed from generic exact Top-1 `24/30` to `23/30`, MRR@10 from `0.87777778`
to `0.86111111`, and same-family accuracy from `41/52` to `40/52`; both also exceeded the absolute
200 ms p95 ceiling. The frozen decision is `winner: null`.

Items 3–4 remain future decisions. Because T5 produced no selected-ranker hash, DRSP-R9 blocks T6;
a future revised experiment requires a new spec and Owner Gate rather than reusing this failed Gate
or calibrating either losing checkpoint.

## G1 acceptance

Requirements, design and tasks are approved together; every adaptive phase is separated; legacy
holdouts are permanently denied; public/private artifact contracts are explicit; metrics and stop
conditions are frozen; and owner-attested rights limitations remain explicit rather than being
silently upgraded to independently verified rights.
