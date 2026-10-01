# AI artifact evaluation — T5-G1 Batches 2–3 progress

Date: 2026-10-01
Scope: generated T5-G1 event／hash／state claims for Batches 2–3 only
Verdict: **PASS — FAITHFUL FIRST-GATE PROGRESS ONLY**

This rubric evaluates whether generated artifacts append Batch 3 without rewriting Batch 2, leaking either
trusted response, or claiming a later Gate.

| Criterion | Result | Evidence and boundary |
|---|---|---|
| State accuracy | PASS | Only ordinals 2／3／8／11／14／18 are `reviewed`; 14 entries remain `staged`, and exact authority remains zero. |
| Authorization fidelity | PASS | Two private batch authorizations back six attestations and six public events; no batch response is represented as three separate owner utterances. |
| Append integrity | PASS | Batch 3 requires the complete Batch 2 predecessor state; existing Batch 2 objects are preserved and the four-output update has rollback coverage. |
| Legacy compatibility | PASS | The prior private ledger shape is migrated only into the bounded append contract, without changing outcome, scope or Gate. |
| Privacy | PASS | Historical and newly added trusted responses and private identity are excluded from public artifacts and tracked content. |
| Replay | PASS | Batch 3 initially returned `created`; two subsequent real checks returned `unchanged`. |
| Gate honesty | PASS | `approved_exact` remains zero; authority bundle／manifest and RHB-T5 authorization remain absent or false. |

## Allowed claims

- T5-G1 Batches 2–3 record six entries as reviewed, leaving 14 staged.
- Batch 3 is a bounded append whose predecessor is the complete Batch 2 decision state.
- Two batch authorizations map to six independently bound attestations and six public review events.
- Historical and newly added response material was included in the public-leak boundary.

## Prohibited claims

- The owner supplied six separate utterances or approved an exact-authority outcome.
- These events establish manufacturer-certified or independent exact product truth.
- Batches 2–3 authorize T5-G2, an authority bundle, benchmark readiness or RHB-T5.
- This PASS measures resolver accuracy, retrieval／ranking quality or model performance.

## Evidence status

Verification covered the `created` operation, two `unchanged` checks, predecessor preservation, cumulative
6／14 state, 2／6／6 private-authorization／attestation／public-event counts, legacy-shape migration, atomic
rollback, and public-leak scans for both historical and new responses. Changed-test strict MyPy initially
reported 7 errors and passed with 0 after correction; that scoped result must not be generalized into a claim
that all repository type debt is resolved. Independent QA recorded focused `22 passed` and a
pre-materialization full-suite result of `1290 passed`; post-materialization checks preserved the Batch 2
event objects and found no decision-response fragments across 794 tracked／unignored files. This documentation
update itself did not rerun tests.

Verdict **PASS** applies only to faithful first-Gate event, hash and state claims. Exact truth, manufacturer
truth, T5-G2 outcomes, resolver accuracy, benchmark readiness and RHB claims remain not evaluated.
