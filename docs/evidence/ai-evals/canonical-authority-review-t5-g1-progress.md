# AI artifact evaluation — T5-G1 Batches 2–7 progress and Batch 1 readiness

Date: 2026-10-01
Scope: generated T5-G1 event／hash／state claims for Batches 2–7 and pre-materialization Batch 1 readiness
Verdict: **PASS — FAITHFUL FIRST-GATE CLAIMS**

This rubric evaluates whether generated artifacts append the two-entry Batch 7 without rewriting Batches 2–6,
leaking a trusted response or private identity, or claiming a later Gate. It also evaluates whether the final
Batch 1 implementation remains inert until a separately explicit owner outcome is supplied.

| Criterion | Result | Evidence and boundary |
|---|---|---|
| State accuracy | PASS | Only 17 bounded entries are `reviewed`; three remain `staged`, and exact authority remains zero. |
| Authorization fidelity | PASS | Six private batch authorizations back 17 attestations and 17 public events; the two-entry batch adds two attestations／events, not a fixed three. |
| Append integrity | PASS | Batch 7 requires the complete Batches 2–6 predecessor prefix; all 15 existing objects are preserved and the four-output update remains atomic. |
| Privacy | PASS | Trusted responses and private identity are excluded from public artifacts and tracked content. |
| Replay | PASS | Batch 7 initially returned `created`; two subsequent real checks returned `unchanged`. |
| Gate honesty | PASS | `approved_exact` remains zero; authority bundle／manifest and RHB-T5 authorization remain absent or false. |
| Batch 1 readiness | PASS | The final path requires the complete Batches 2–7 state; synthetic tests reach 20／0 without mutating real state, while generic continuation remains insufficient. |

## Allowed claims

- T5-G1 Batches 2–7 record 17 entries as reviewed, leaving three staged.
- Batch 7 is a two-entry bounded append whose predecessor is the complete Batches 2–6 decision prefix.
- Six batch authorizations map to 17 independently bound attestations and 17 public review events.
- Existing Batches 2–6 decision objects were preserved.
- The three remaining staged entries are Batch 1 Mazda Autozam ordinals `1`, `10` and `16`.
- Batch 1 recorder readiness is verified, but no real Batch 1 event or authorization has been materialized.

## Prohibited claims

- Seventeen separate utterances were supplied, every batch has three records, or an exact-authority outcome was approved.
- These events establish manufacturer-certified or independent exact product truth.
- Batches 2–7 complete T5-G1 or authorize T5-G2, an authority bundle, benchmark readiness or RHB-T5.
- This PASS measures resolver accuracy, retrieval／ranking quality or model performance.

## Evidence status

Available verification covered the Batch 7 `created` operation, two `unchanged` checks, predecessor preservation,
cumulative 17／3 state, 6／17／17 private-authorization／attestation／public-event counts, two-entry dynamic counting,
atomic output handling, and the continued absence of exact authority, bundle／manifest and RHB authorization.
Independent pre-materialization QA recorded focused `60 passed` and a full-suite result of `1328 passed`; the only
message was an existing dependency warning. This documentation update itself did not rerun tests.

Independent post-materialization QA also passed: all 17 decision links were valid; the prior 15 events, candidate
objects and attestation hashes were preserved; permission, Git-ignore and bytes-stable replay checks passed; and a
794-file privacy scan covering all six real authorization inputs found no tracked or unignored disclosure. Blocker
and Important findings were both zero.

Batch 1 pre-materialization QA recorded `71 passed` for the focused recorder suite and `1339 passed` for the full
repository. Ruff, format, strict MyPy, compileall and diff checks passed; the only warning was the existing
Starlette／AnyIO deprecation. These tests used synthetic `TEST-ONLY` owner text and did not change the real
17-reviewed／3-staged state.

Batch 4 previously exposed a shared-workspace tasks／manifest update race and passed after a stable rerun; that
known orchestration risk remains documented. Batch 7 materialization evidence confirms preservation of the 15 prior
objects and idempotent replay. No supplied evidence authorizes claims beyond these bounded checks.

Verdict **PASS** applies only to faithful first-Gate event, hash and state claims already evidenced. Exact truth,
manufacturer truth, T5-G1 completion, T5-G2 outcomes, resolver accuracy, benchmark readiness and RHB claims remain
not evaluated.
