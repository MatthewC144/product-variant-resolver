# Serper dual-source runtime readiness v1 — Tasks

- [x] **SDSRR-T1** Implement frozen aggregate readiness validation. _(→R1–R5, R7–R8)_
  - Files: `src/product_variant_resolver/serper_dual_source_runtime_readiness.py`
  - Acceptance: existing frozen inputs reproduce one fail-closed readiness payload without scoring.
- [x] **SDSRR-T2** Materialize the aggregate-only readiness artifact. _(→R5–R8)_
  - Files: `data/evaluation/serper-dual-source-runtime-readiness-v1/readiness.json`
  - Acceptance: artifact is immutable, contains no row-level data and names one next data contract.
- [x] **SDSRR-T3** Add focused unit and integrity tests. _(→R1–R8)_
  - Files: `tests/evaluation/test_serper_dual_source_runtime_readiness.py`
  - Acceptance: reproduction, mutation rejection, privacy and no-runtime boundaries pass.
- [x] **SDSRR-T4** Record QA, AI-eval evidence and Project Log. _(→R3–R8)_
  - Files: `review.md`, `docs/evidence/ai-evals/`, `docs/PROJECT-LOG.md`
  - Acceptance: limitations and the next permitted action are independently understandable.
