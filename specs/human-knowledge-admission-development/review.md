# QA review — Human Knowledge admission-policy development v1

Date: 2026-09-20. Verdict: **PASS for experiment integrity; FAIL to select a mitigation**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| R1–R4 | Frozen protocol, five fixed thresholds, token-match unit tests | PASS |
| R2 | 199 + 24 dev cases, no private local path | PASS |
| R5 | Exact recall/governance gates recomputed for every configuration | PASS |
| R6 | Eligible/min-forbidden/lowest-threshold ordering is deterministic | PASS |
| R7 | 223 retrieval calls feed all five settings; check mode never retrieves | PASS |
| R8 | Retriever/runtime/API/SQL/private evaluation unchanged | PASS |

## Findings

Baseline is the only eligible configuration and is selected by the frozen ordering, but it is not a
mitigation: it preserves 168/168 old positives and 24/24 new required hits while retaining 18/24
forbidden cases. Coverage 0.5 reduces forbidden cases to 7 but loses one old positive. Coverage 2/3
reduces them to 2 but loses three old positives. Coverage 0.75 and 1.0 remove all forbidden cases but
lose respectively 9/1 and 16/2 old/new required hits. The simple global filter cannot satisfy both
recall and safety.

Fifteen focused and all 726 repository tests pass. Targeted Ruff/format, MyPy, compile, protocol and
report checks pass. The known Starlette/AnyIO deprecation warning remains.

## Carry forward

Return to design, not runtime integration. The next development version should compare a
candidate-relative penalty or reranker that uses unmatched distinctive tokens without hard-deleting
abbreviation/typo candidates. Preserve this v1 grid as a failed alternative and freeze a new protocol
before measuring v2.
