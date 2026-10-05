# Pointwise three-class development calibration — QA review

Date: 2026-10-05. Mode: Lite / Lean Industrial. Verdict: **PASS — development only**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| PTCDC-R1 | PNMR-G1 authorization/overlay, positive/negative splits, source and model hashes validate before scoring. | PASS |
| PTCDC-R2 | Fit composition is exactly 70 catalog-present + 32 no-match rows. | PASS |
| PTCDC-R3 | Selection composition is exactly 30 catalog-present + 20 no-match rows. | PASS |
| PTCDC-R4 | Match gate accepts 7/50 with 7 correct: 100% precision. | PASS |
| PTCDC-R5 | No-match gate predicts 10/50 with 9 correct: 90% precision, 45% recall and 3.33% false-no-match rate. | PASS |
| PTCDC-R6 | Unit test proves an infeasible no-match gate raises a shortfall instead of relaxing constraints. | PASS |
| PTCDC-R7 | Recursive checker rejects row-level keys; tracked artifacts contain aggregate values only. | PASS |
| PTCDC-R8 | Final read/score counts are zero, runtime flags are false, and API test returns 503 if v2 is configured. | PASS |

## Verification

Sixty-seven relevant tests passed, along with Ruff and strict MyPy. Both v1 and v2 artifact CLI
checks pass. A second in-memory run over all 152 development rows reproduced the calibration and
policy bytes exactly. The harmless local model warning about deprecated `torch_dtype` remains in the
third-party loading path and does not affect results.

## Findings and limitation

No release blocker exists inside the authorized development scope. The policy is intentionally
conservative: only 17/50 selection rows receive a decisive status and 33 are ambiguous. More
importantly, the 20 negative selection rows participated in threshold choice, so their metrics are
development-selection evidence, not untouched test performance. The existing 53-case final ranking
partition contains catalog-present cases only and cannot independently validate no-match behavior.

## Next permitted action

Do not activate runtime. The next necessary evidence, if deployment is desired, is an independently
governed untouched no-match holdout combined with a fixed catalog-present policy test. That future
gate must use the frozen v2 artifacts without changing model, features or thresholds.
