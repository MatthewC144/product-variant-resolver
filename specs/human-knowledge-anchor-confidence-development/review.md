# QA review — Human Knowledge rank-1 anchor confidence v4

Date: 2026-09-21. Verdict: **implementation PASS; policy selection FAIL**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| R1–R2 | Frozen 10-positive/12-negative public pack, complete source hashes, no private paths | PASS |
| R3 | Exactly 22 retrieval calls, one per frozen query; raw rows reused by all settings | PASS |
| R4–R5 | Frozen confidence formula, secondary 0.75 gate, source order, ten-setting grid | PASS |
| R6–R7 | Existing regression, anchor recall, absence, and error gates recomputed | PASS |
| R8 | Deterministic selection returns no winner because no setting is eligible | PASS |
| R9 | No runtime, API, database, canonical, release, color, or private-evaluation change | PASS |

## Findings

The pack and protocol were frozen before the new retrieval. Their files explicitly record
`retrieval_executed: false`; the result records exactly 22 calls and 42 source candidates. Every
configuration is scored from those same raw rows plus the already committed 223 public rows.

The confidence formula cannot separate valid noisy anchors from plausible but absent castings.
At threshold 0.61, recall gates remain intact (168/168 existing and 10/10 anchor positives), but
10/12 missing identities still produce output. At 0.625, recall falls to 167/168 and 9/10 without
improving the ten unsafe negative cases. At 0.75, four negative cases remain nonempty while recall
is still 167/168 and 9/10. Consequently all ten settings are ineligible and `winner` is null.

Nine focused tests and all 770 repository tests pass. Ruff, formatting, MyPy, compile, artifact
integrity, installed CLI, and byte-idempotent check modes pass. The existing Starlette/AnyIO
deprecation warning remains and is unrelated to this feature.

## Carry forward

Do not run another private evaluation or activate v3/v4 admission. A next public-development design
needs a candidate-specific contradiction or identity-span model, not another scalar threshold over
the same two overlapping signals. It must use new public evidence, freeze its cases and protocol
before retrieval, and preserve the private evaluation as untouched final evidence.
