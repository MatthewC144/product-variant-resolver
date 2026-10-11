# Serper dual-source evaluation v1 — Lean QA review

Date: 2026-10-10. Scope: SDSE-T1–T4 including the one-shot final test. Verdict: **PASS**.

## Requirement coverage

| Requirement | Evidence | Result |
| --- | --- | --- |
| SDSE-R1–R3 | Frozen dataset/split loaders; dataset and assignment hashes | PASS |
| SDSE-R4 | Artifact guardrail `test_targets_scored=0`; no test execution path used | PASS |
| SDSE-R7 | Aggregate-only artifact and forbidden row-key scan | PASS |
| SDSE-R8 | Same RRF Top-25 membership, frozen MiniLM binding, RRF baseline reproduction | PASS |
| SDSE-R9 | Frozen owner authorization, one completed run, aggregate-only final and rerun guard | PASS |

## Verification

- 20 focused tests passed in `tests/evaluation/test_serper_dual_source_evaluation.py`.
- Ruff passed for the implementation and focused tests.
- strict MyPy passed for the implementation and focused tests.
- Frozen artifact loader recomputes every reported accuracy/recall/MRR value from raw aggregate
  counts, verifies deltas and rejects byte drift.
- The previously frozen RRF counts reproduced exactly for Image raw and Shopping raw.
- Final aggregate metrics are recomputed from the four 50-case raw-count groups; owner/model/split
  bindings and Pointwise-minus-RRF deltas are validated.
- The final output exists, so a second SDSE-T4 call fails before loading the dataset or model.
- API key, URLs, row-level queries, targets, labels, candidates and predictions are absent from the
  result artifact.

## Carry-forward

The benchmark workflow is complete. The result selects Pointwise for ranking evidence only; runtime
activation would require a separate policy/calibration and operational decision. Existing
repository-wide frozen artifact integrity failures involving historical `.gitignore`/runtime-source
hashes are separate maintenance debt and were not modified in this task.
