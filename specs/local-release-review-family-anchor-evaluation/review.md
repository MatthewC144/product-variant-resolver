# QA review — Local review-family anchored admission evaluation v2

Date: 2026-09-21. Verdict: **FAIL; return to public development design**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| R1 | Exact v3 policy/configuration, protocol, and selection hashes | PASS |
| R2–R3 | Immutable v1 private/public hashes; zero new retrieval calls | PASS |
| R4 | Rank-1 anchor and 0.75 secondary gate applied in source order | PASS |
| R5 | Seven precommitted gates recomputed from private case evidence | FAIL: two forbidden rank-1 hits |
| R6–R7 | Separate ignored result; aggregate-only public output; create-once/check | PASS |
| R8 | Runtime/canonical/release/color/PostgreSQL downstream effects all zero | PASS |

## Findings

The policy preserves all 15 positive hits, 13 rank-1 positives, all five local-family coverage, and
zero retrieval/admission errors. It reduces forbidden hits from the immutable v1 baseline of three
to two by removing one secondary false positive. The remaining two forbidden candidates are source
rank 1 and are deliberately protected by the anchor, so both hard-negative gates fail.

The failure is not a reason to tune `0.75`: no secondary threshold can remove an anchored rank-1
candidate. It identifies the next design problem—rank-1 candidates need their own compatibility or
confidence decision while valid low-coverage rank-1 typo cases remain protected. The private cases
must not be inspected for a hand-authored exception or reused as v4 development labels.

Ten focused and all 761 repository tests pass. Targeted Ruff/format, MyPy, compile, protocol, public
privacy, deterministic check, and no-reretrieval checks pass. The known Starlette/AnyIO deprecation
warning remains.

## Carry forward

Return to public development data and design an anchor-confidence v4 policy with separate cases for
valid low-coverage rank-1 candidates and wrong rank-1 candidates. Freeze and select it publicly
before creating another private-evaluation version. Runtime integration and API changes remain
blocked.
