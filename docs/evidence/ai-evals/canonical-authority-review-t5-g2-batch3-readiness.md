# AI artifact evaluation — T5-G2 Batch 3 readiness

Date: 2026-10-02
Scope: Batch 3 recorder behavior and readiness claims
Verdict: **PASS — READY WITHOUT PRE-AUTHORIZATION**

| Criterion | Result | Evidence and boundary |
|---|---|---|
| Frozen scope | PASS | Only Subaru BRZ ordinals 3, 8 and 14 with identifiers JBB55, HYY12 and HYW99 are accepted. |
| Prefix integrity | PASS | Batch 3 requires complete Batches 1–2; a missing Batch 2 and unsupported Batch 4 fail closed. |
| Fresh authorization | PASS | A future Batch 3 response must differ from the corresponding T5-G1 response. |
| Historical preservation | PASS | Tests preserve both prior authorizations, six attestations/events and all non-target candidates. |
| Field fidelity | PASS | Six supported rows are bound; color/edition stay null and Zamac/color context is not promoted. |
| Replay | PASS | All three supported batches replay unchanged without removing later history. |
| Privacy | PASS | Tests use synthetic responses; both real responses have zero hits in 802 tracked/unignored files. |
| Gate honesty | PASS | No Batch 3 outcome, bundle freeze, CAR-T6 or RHB-T5 authorization is claimed. |

## Allowed claims

- The bounded T5-G2 Batch 3 append path is implemented and verified.
- The three Subaru BRZ entries have six agreeing frozen-snapshot evidence rows.
- A qualifying future decision would produce three additional exact events.
- The real state remains unchanged at 6 exact / 14 reviewed.

## Prohibited claims

- Batch 3 is already approved or materialized.
- Zamac or color-context wording proves a color or edition.
- Snapshot-relative agreement is manufacturer-certified truth.
- Readiness authorizes CAR-T5F, CAR-T6, RHB-T5 or measures resolver/RAG quality.

## Verification record

Focused verification reported `18 passed`; the complete repository reported `1357 passed, 1
warning`. Ruff, formatting, strict MyPy, compileall and diff checks passed. The only warning was an
existing Starlette/AnyIO deprecation. Real Batch 2 replay stayed unchanged, the real state remained
6 exact / 14 reviewed, and the privacy scan found zero real-response hits.

This PASS applies only to readiness and claim faithfulness. A real Batch 3 outcome remains a
separate owner decision.
