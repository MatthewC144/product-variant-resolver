# QA review — Human Knowledge anchored compatibility admission v3

Date: 2026-09-20. Verdict: **PASS for public-development selection; private validation pending**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| R1–R2 | Frozen v2 report/source hashes; no private paths or artifacts | PASS |
| R3 | Validated v2 raw pools reused; new retrieval calls equal zero | PASS |
| R4–R5 | Rank-1 anchor, source-order preservation, eight frozen secondary thresholds | PASS |
| R6–R7 | Exact recall/governance gates and deterministic selection recomputed | PASS |
| R8 | Upstream bytes, admitted/abstained ranks, result and Markdown checks | PASS |
| R9 | Winner scope restricted to a new private shadow evaluation | PASS |

## Findings

Thresholds through 0.75 preserve 168/168 existing positives, 24/24 new required targets, all four
merge controls, zero existing governance violations, zero unrelated results, and zero errors. The
forbidden count falls from 18 at baseline to 16/8/7/2/2/0 as secondary coverage tightens. Threshold
1.0 also has zero forbidden cases but loses one existing positive and is ineligible.

The frozen rule selects `secondary-075`, the lowest eligible threshold with zero forbidden cases. It
admits 212 of 329 source Top-5 candidates and abstains from 117 secondary candidates. All 24 new
required targets remain rank 1; the three old targets below rank 1 have coverage 1, 1, and 0.75 and
remain admitted. This is a development qualification, not final evidence. Because rank 1 is always
admitted, an unseen wrong rank-1 candidate is the most important unresolved risk.

Twelve focused and all 751 repository tests pass. Targeted Ruff/format, MyPy, compile, protocol,
report, installed CLI, and retrieval-free check modes pass. The known Starlette/AnyIO deprecation
warning remains.

## Carry forward

Freeze a new private shadow-evaluation version before applying `secondary-075`. Do not overwrite the
existing 20-case FAIL, use it to revise the policy, or integrate runtime. The new evaluation must
report positive recall, family coverage, forbidden hits, rank-1 forbidden behavior, and zero
retrieval errors under immutable gates. A failure returns to development design; only a pass may
advance to opt-in runtime planning.
