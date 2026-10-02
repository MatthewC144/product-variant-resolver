# AI artifact evaluation — T5-G1 completion

Date: 2026-10-01
Scope: generated T5-G1 event／hash／state claims for all seven family batches
Verdict: **PASS — FAITHFUL FIRST-GATE CLAIMS**

This rubric evaluates whether the final Batch 1 append completes the bounded first Gate without rewriting prior
objects, leaking trusted responses or private identity, or claiming an exact-authority／RHB result.

| Criterion | Result | Evidence and boundary |
|---|---|---|
| State accuracy | PASS | Exactly 20 bounded entries are `reviewed`, zero remain `staged`, and exact authority remains zero. |
| Authorization fidelity | PASS | Seven private batch authorizations back 20 independently bound attestations and 20 public events. |
| Append integrity | PASS | Final Batch 1 requires the complete Batches 2–7 predecessor state; all 17 prior events and reviewed candidate objects are preserved. |
| Link integrity | PASS | All 20 candidate→event→attestation→authorization links validate against the frozen packet and catalog. |
| Privacy | PASS | A 794-file tracked／unignored scan found no real trusted response; private ledgers remain Git-ignored with restrictive permissions. |
| Replay | PASS | The real append returned `created`; two subsequent exact checks returned `unchanged`. |
| Gate honesty | PASS | `approved_exact` remains zero; authority bundle／manifest and RHB-T5 authorization remain absent or false. |

## Allowed claims

- T5-G1 records all 20 bounded entries as reviewed across seven family batches.
- Seven batch authorizations map to 20 independently bound attestations and 20 public review events.
- Final Batch 1 was appended only after the complete 17-entry Batches 2–7 predecessor state.
- Existing 17 review events and reviewed candidate objects were preserved.
- T5-G1 is complete and T5-G2 has not started.

## Prohibited claims

- T5-G1 created exact authority, manufacturer-certified truth or an authority bundle／manifest.
- A T5-G1 or catalog-application response may be reused for T5-G2.
- T5-G1 completion authorizes CAR-T6, benchmark readiness or RHB-T5.
- This PASS measures resolver accuracy, retrieval／ranking quality or model performance.

## Evidence status

Pre-materialization verification recorded focused `71 passed` and full-suite `1339 passed`, with Ruff, format,
strict MyPy, compileall and diff checks passing. The only warning was an existing Starlette／AnyIO deprecation.

Post-materialization verification covered the `created` operation, two `unchanged` checks, 20／0 candidate state,
7／20／20 authorization-attestation-event counts, all 20 links, preservation of 17 prior events and candidate
objects, permission／Git-ignore boundaries, forbidden bundle absence and a 794-file privacy scan with zero hits.
The full suite was not rerun after the state-only materialization.

Verdict **PASS** applies only to faithful T5-G1 first-Gate event, hash and state claims. Exact truth, T5-G2,
authority freezing, resolver quality, RHB-T4 re-audit and RHB-T5 remain not evaluated or unauthorized.
