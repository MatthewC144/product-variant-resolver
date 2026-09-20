# QA review — Human Knowledge candidate-relative reranker v2

Date: 2026-09-20. Verdict: **PASS for experiment integrity; FAIL to select a mitigation**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| R1–R2 | Protocol/source hashes frozen before collection; public 142-document corpus only | PASS |
| R3 | Exactly 223 Top-25 retrieval calls; seven settings reuse the same pools | PASS |
| R4–R5 | Frozen score formula, seven weights, no coverage-based hard deletion | PASS |
| R6–R7 | Exact recall/governance gates and deterministic winner ordering recomputed | PASS |
| R8 | Raw rank/score/coverage checks and retrieval-free report check | PASS |
| R9 | Runtime, API, PostgreSQL, canonical truth, and private evaluation unchanged | PASS |

## Findings

Every weight from 0 through 2 preserves 168/168 old positives, 24/24 new required targets, all four
merge controls, and zero governance violations, unrelated results, or retrieval errors. Every weight
also leaves the forbidden count at 18/24. The frozen selector therefore returns baseline, which is
not an improved mitigation.

The result is structural rather than a weight-tuning issue. Only five of 223 raw candidate pools
contain more than five items. Among the 24 safety cases, the median pool has three candidates and
only two pools exceed five. A reranker can demote an unsupported item, but when the entire pool has
two to four items it cannot move that item outside Top 5 without an explicit admission/abstention
decision. Increasing the penalty after seeing this result would not solve that boundary.

Thirteen focused and all 739 repository tests pass. Targeted Ruff/format, MyPy, compile, protocol,
report, and deterministic check modes pass. The known Starlette/AnyIO deprecation warning remains.

## Carry forward

Preserve this v2 report as a failed alternative. The next design must jointly decide ranking and
whether a lower candidate should be returned at all—for example a query-candidate compatibility
admission model with explicit abstention—while preserving the three old positive cases that are not
rank 1. Freeze a new development protocol before testing it. Do not consult the immutable private
20-case evaluation until a public-development policy qualifies.
