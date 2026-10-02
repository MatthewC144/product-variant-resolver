# AI artifact evaluation — T5-G2 Batch 2 readiness

Date: 2026-10-02
Scope: Batch 2 recorder behavior and generated readiness claims
Verdict: **PASS — READY WITHOUT PRE-AUTHORIZATION**

| Criterion | Result | Evidence and boundary |
|---|---|---|
| Frozen scope | PASS | Only Draftnator ordinals 2, 11 and 18 with identifiers HYW70, HYX67 and HYY31 are accepted. |
| Prefix integrity | PASS | Batch 2 requires the complete Batch 1 prefix; skipping Batch 1 and unsupported Batch 3 fail closed. |
| Fresh authorization | PASS | Batch 2 must use a new response distinct from its corresponding T5-G1 response. |
| Historical preservation | PASS | Tests preserve the Batch 1 authorization, attestations, events and every non-target candidate object. |
| Field fidelity | PASS | Exact scope contains the six supported rows; color/edition remain null and color-context text is not promoted. |
| Atomicity/replay | PASS | Interrupted append restores all four artifacts; replay of Batch 1 or 2 is unchanged and retains later history. |
| Privacy | PASS | Synthetic responses are used in tests; the real response has zero hits in 798 tracked/unignored text files. |
| Gate honesty | PASS | No Batch 2 outcome, bundle freeze, CAR-T6 or RHB-T5 authorization is claimed. |

## Allowed claims

- The code path for a bounded T5-G2 Batch 2 append is implemented and verified.
- The three Draftnator entries have six agreeing frozen-snapshot evidence rows.
- A qualifying future decision would produce three additional `reviewed -> approved_exact` events.
- The real state is unchanged while waiting at the Owner Gate.

## Prohibited claims

- Batch 2 is already approved or materialized.
- Color or edition is known from second/third-color context text.
- Snapshot-relative agreement is manufacturer-certified truth.
- Readiness authorizes CAR-T5F, CAR-T6, RHB-T5 or proves resolver/RAG quality.

## Verification record

Focused verification reported `16 passed`; the complete repository reported `1355 passed, 1
warning`. Ruff, formatting, strict MyPy, compileall and diff checks passed. The only warning was an
existing Starlette/AnyIO deprecation. A real Batch 1 replay remained `unchanged`, the real state
remained 3 approved exact / 17 reviewed, and the privacy scan found zero owner-response hits.

Verdict **PASS** applies only to readiness and claim faithfulness. A real Batch 2 outcome remains a
separate owner decision.
