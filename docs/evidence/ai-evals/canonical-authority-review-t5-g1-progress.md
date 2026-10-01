# AI artifact evaluation — T5-G1 Batches 2–6 progress

Date: 2026-10-01
Scope: generated T5-G1 event／hash／state claims for Batches 2–6 only
Verdict: **PASS — FAITHFUL FIRST-GATE CLAIMS**

This rubric evaluates whether generated artifacts append Batch 6 without rewriting Batches 2–5, leaking a
trusted response or private identity, or claiming a later Gate.

| Criterion | Result | Evidence and boundary |
|---|---|---|
| State accuracy | PASS | Only 15 bounded entries are `reviewed`; five remain `staged`, and exact authority remains zero. |
| Authorization fidelity | PASS | Five private batch authorizations back 15 attestations and 15 public events; a batch response is not represented as three separate utterances. |
| Append integrity | PASS | Batch 6 requires the complete Batches 2–5 predecessor prefix; all existing objects are preserved and the four-output update remains atomic. |
| Privacy | PASS | Trusted responses and private identity are excluded from public artifacts and tracked content. |
| Replay | PASS | Batch 6 initially returned `created`; two subsequent real checks returned `unchanged`. |
| Gate honesty | PASS | `approved_exact` remains zero; authority bundle／manifest and RHB-T5 authorization remain absent or false. |

## Allowed claims

- T5-G1 Batches 2–6 record 15 entries as reviewed, leaving five staged.
- Batch 6 is a bounded append whose predecessor is the complete Batches 2–5 decision prefix.
- Five batch authorizations map to 15 independently bound attestations and 15 public review events.
- Existing Batches 2–5 decision objects were preserved.

## Prohibited claims

- Fifteen separate utterances were supplied, or an exact-authority outcome was approved.
- These events establish manufacturer-certified or independent exact product truth.
- Batches 2–6 authorize T5-G2, an authority bundle, benchmark readiness or RHB-T5.
- This PASS measures resolver accuracy, retrieval／ranking quality or model performance.

## Evidence status

Available verification covered the Batch 6 `created` operation, two `unchanged` checks, predecessor preservation,
cumulative 15／5 state, 5／15／15 private-authorization／attestation／public-event counts, atomic output handling,
and the continued absence of exact authority, bundle／manifest and RHB authorization. Independent pre-
materialization QA recorded focused `72 passed` and a full-suite result of `1317 passed`; the only message was
an existing dependency warning. This documentation update itself did not rerun tests.

Batch 4 previously exposed a shared-workspace tasks／manifest update race and passed after a stable rerun; that
known orchestration risk remains documented. Batch 6 materialization evidence confirms the 5／15／15 cumulative
counts, preservation of the 12 prior objects, and idempotent replay. Post-materialization QA returned **PASS**:
focused `72 passed`; all 15 candidate-to-authorization links, 35 item hashes and four top-level hashes were
valid; permissions, Git-ignore and forbidden-output checks passed; and five private responses had zero hits
across 794 tracked／unignored files. Blocker, Important and Later findings were all zero.

Verdict **PASS** applies only to faithful first-Gate event, hash and state claims already evidenced. Exact truth, manufacturer
truth, T5-G2 outcomes, resolver accuracy, benchmark readiness and RHB claims remain not evaluated.
