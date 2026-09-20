# QA review — Human Knowledge false-positive development v1

Date: 2026-09-20. Verdict: **PASS for baseline construction; no mitigation verdict**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| R1–R4 | Builder resolves 24 public-corpus pairs, requires shared core tokens, rejects exact queries | PASS |
| R5 | Pack/manifest and all source hashes reproduce byte for byte | PASS |
| R6 | Frozen v4 baseline reports required and forbidden ranks for 24/24 cases | PASS |
| R7 | Output status is baseline-only and contains no threshold/winner | PASS |
| R8 | No API, runtime, database, canonical, or private-evaluation path changed | PASS |
| R9 | Create-once/check/idempotency and partial-directory tests | PASS |

## Findings

The current retriever returns every required target at rank 1, but also returns the specified
forbidden target in 18 of 24 Top-5 lists. This is an expected diagnostic baseline, not a test-suite
failure. The result supports a separate mitigation experiment but does not identify or approve a
policy.

Twelve focused tests and all 711 repository tests pass. Targeted Ruff, formatting, MyPy, compile,
artifact check, and diff checks pass. The known Starlette/AnyIO deprecation warning remains.

## Carry forward

Build a versioned admission-policy grid using this development pack plus the existing 199-case
positive development pack. Preserve required recall and existing governance controls while reducing
forbidden admissions. Do not load or rerun the private local-family evaluation during selection.
