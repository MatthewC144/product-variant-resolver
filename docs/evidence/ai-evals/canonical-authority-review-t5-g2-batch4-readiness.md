# AI artifact evaluation — T5-G2 Batch 4 readiness

Date: 2026-10-02
Scope: Batch 4 recorder behavior and readiness claims
Verdict: **PASS — READY WITHOUT PRE-AUTHORIZATION**

| Criterion | Result | Evidence and boundary |
|---|---|---|
| Frozen scope | PASS | Only Nissan Skyline ordinals 4, 13 and 20 with identifiers HYX54, HYW79 and HYY30 are accepted. |
| Prefix integrity | PASS | Batch 4 requires complete Batches 1–3; a missing Batch 3 and unsupported Batch 5 fail closed. |
| Fresh authorization | PASS | A future Batch 4 response must differ from the corresponding T5-G1 response. |
| Historical preservation | PASS | Tests preserve three prior authorizations, nine attestations/events and non-target candidates. |
| Field fidelity | PASS | Six supported rows are bound; color/edition stay null and color context is not promoted. |
| Replay | PASS | All four supported batches replay unchanged without removing later history. |
| Privacy | PASS | Tests use synthetic responses; all three real responses have zero hits in 806 tracked/unignored files. |
| Gate honesty | PASS | No Batch 4 outcome, bundle freeze, CAR-T6 or RHB-T5 authorization is claimed. |

## Allowed claims

- The bounded T5-G2 Batch 4 append path is implemented and verified.
- The three Nissan Skyline entries have six agreeing frozen-snapshot evidence rows.
- A qualifying future decision would produce three additional exact events.
- The real state remains unchanged at 9 exact / 11 reviewed.

## Prohibited claims

- Batch 4 is already approved or materialized.
- Color-context wording proves a color or edition.
- Snapshot-relative agreement is manufacturer-certified truth.
- Readiness authorizes CAR-T5F, CAR-T6, RHB-T5 or measures resolver/RAG quality.

## Verification record

Focused verification reported `20 passed`; the complete repository reported `1359 passed, 1
warning`. Ruff, formatting, strict MyPy, compileall and diff checks passed. The only warning was an
existing Starlette/AnyIO deprecation. Real Batch 3 replay stayed unchanged, the real state remained
9 exact / 11 reviewed, and the privacy scan found zero real-response hits.

This PASS applies only to readiness and claim faithfulness. A real Batch 4 outcome remains a
separate owner decision.
