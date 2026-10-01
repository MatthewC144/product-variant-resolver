# AI artifact evaluation — T5-G1 Batches 2–4 progress

Date: 2026-10-01
Scope: generated T5-G1 event／hash／state claims for Batches 2–4 only
Verdict: **PASS — FAITHFUL FIRST-GATE PROGRESS ONLY**

This rubric evaluates whether generated artifacts append Batch 4 without rewriting Batches 2–3, leaking a
trusted response or private identity, or claiming a later Gate.

| Criterion | Result | Evidence and boundary |
|---|---|---|
| State accuracy | PASS | Only nine bounded entries are `reviewed`; 11 remain `staged`, and exact authority remains zero. |
| Authorization fidelity | PASS | Three private batch authorizations back nine attestations and nine public events; a batch response is not represented as three separate utterances. |
| Append integrity | PASS | Batch 4 requires the complete Batches 2–3 predecessor prefix; all existing objects are preserved and the four-output update remains atomic. |
| Privacy | PASS | Trusted responses and private identity are excluded from public artifacts and tracked content. |
| Replay | PASS | Batch 4 initially returned `created`; two subsequent real checks returned `unchanged`. |
| Gate honesty | PASS | `approved_exact` remains zero; authority bundle／manifest and RHB-T5 authorization remain absent or false. |

## Allowed claims

- T5-G1 Batches 2–4 record nine entries as reviewed, leaving 11 staged.
- Batch 4 is a bounded append whose predecessor is the complete Batches 2–3 decision prefix.
- Three batch authorizations map to nine independently bound attestations and nine public review events.
- Existing Batches 2–3 decision objects were preserved.

## Prohibited claims

- Nine separate utterances were supplied, or an exact-authority outcome was approved.
- These events establish manufacturer-certified or independent exact product truth.
- Batches 2–4 authorize T5-G2, an authority bundle, benchmark readiness or RHB-T5.
- This PASS measures resolver accuracy, retrieval／ranking quality or model performance.

## Evidence status

Verification covered the Batch 4 `created` operation, two `unchanged` checks, predecessor preservation,
cumulative 9／11 state, 3／9／9 private-authorization／attestation／public-event counts, atomic output handling,
and the continued absence of exact authority, bundle／manifest and RHB authorization. Independent pre-
materialization QA recorded focused `53 passed` and a full-suite result of `1298 passed`. This documentation
update itself did not rerun tests.

Post-materialization QA is **PASS WITH RISKS**: a first focused run overlapped the tasks／manifest update and
observed 23 failures from one transient binding mismatch; after the shared-workspace update completed, the
binding matched and the stable rerun passed `30/30`. Formal decision links, prior-object preservation,
permissions and privacy checks passed, so this is retained as an orchestration race rather than interpreted
as a Batch 4 state failure.

Verdict **PASS** applies only to faithful first-Gate event, hash and state claims. Exact truth, manufacturer
truth, T5-G2 outcomes, resolver accuracy, benchmark readiness and RHB claims remain not evaluated.
