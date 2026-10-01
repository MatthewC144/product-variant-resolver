# AI artifact evaluation — T5-G1 Batches 2–5 progress

Date: 2026-10-01
Scope: generated T5-G1 event／hash／state claims for Batches 2–5 only
Verdict: **PASS — FAITHFUL FIRST-GATE CLAIMS**

This rubric evaluates whether generated artifacts append Batch 5 without rewriting Batches 2–4, leaking a
trusted response or private identity, or claiming a later Gate.

| Criterion | Result | Evidence and boundary |
|---|---|---|
| State accuracy | PASS | Only 12 bounded entries are `reviewed`; eight remain `staged`, and exact authority remains zero. |
| Authorization fidelity | PASS | Four private batch authorizations back 12 attestations and 12 public events; a batch response is not represented as three separate utterances. |
| Append integrity | PASS | Batch 5 requires the complete Batches 2–4 predecessor prefix; all existing objects are preserved and the four-output update remains atomic. |
| Privacy | PASS | Trusted responses and private identity are excluded from public artifacts and tracked content. |
| Replay | PASS | Batch 5 initially returned `created`; two subsequent real checks returned `unchanged`. |
| Gate honesty | PASS | `approved_exact` remains zero; authority bundle／manifest and RHB-T5 authorization remain absent or false. |

## Allowed claims

- T5-G1 Batches 2–5 record 12 entries as reviewed, leaving eight staged.
- Batch 5 is a bounded append whose predecessor is the complete Batches 2–4 decision prefix.
- Four batch authorizations map to 12 independently bound attestations and 12 public review events.
- Existing Batches 2–4 decision objects were preserved.

## Prohibited claims

- Twelve separate utterances were supplied, or an exact-authority outcome was approved.
- These events establish manufacturer-certified or independent exact product truth.
- Batches 2–5 authorize T5-G2, an authority bundle, benchmark readiness or RHB-T5.
- This PASS measures resolver accuracy, retrieval／ranking quality or model performance.

## Evidence status

Available verification covered the Batch 5 `created` operation, two `unchanged` checks, predecessor preservation,
cumulative 12／8 state, 4／12／12 private-authorization／attestation／public-event counts, atomic output handling,
and the continued absence of exact authority, bundle／manifest and RHB authorization. Independent pre-
materialization QA recorded focused `62 passed` and a full-suite result of `1307 passed`. This documentation
update itself did not rerun tests.

Batch 4 previously exposed a shared-workspace tasks／manifest update race and passed after a stable rerun. That
known orchestration risk remains documented and was not reproduced in Batch 5. Post-materialization QA
returned **PASS** after verifying all 12 event／attestation／authorization／candidate links, preservation of
the nine prior objects, permissions, Git-ignore, replay, and zero response hits across 794 tracked／unignored
files. Blocker, Important and Later findings were all zero.

Verdict **PASS** applies only to faithful first-Gate event, hash and state claims already evidenced. Exact truth, manufacturer
truth, T5-G2 outcomes, resolver accuracy, benchmark readiness and RHB claims remain not evaluated.
