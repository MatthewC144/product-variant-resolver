# AI artifact evaluation — T5-G2 Batches 6–7 readiness

Date: 2026-10-03
Scope: Batch 6 and Batch 7 recorder behavior and readiness claims
Verdict: **PASS — BOTH PATHS READY WITHOUT PRE-AUTHORIZATION**

| Criterion | Result | Evidence and boundary |
|---|---|---|
| Batch 6 scope | PASS | Only Morgan Super 3 ordinals 6, 12 and 19 with identifiers HYX48, HYW13 and HYY33 are accepted. |
| Batch 7 scope | PASS | Only Mazda MX-5 Miata ordinals 9 and 15 with identifiers HYW18 and HYX57 are accepted. |
| Prefix integrity | PASS | Batch 6 requires Batches 1–5; Batch 7 requires Batches 1–6; unsupported Batch 8 fails closed. |
| Separate authorization | PASS | The two batches require different fresh responses; Batch 7 cannot precede Batch 6. |
| Historical preservation | PASS | Tests preserve every prior authorization, attestation, event and non-target candidate object. |
| Field fidelity | PASS | Each entry binds six agreeing fields; color and edition remain null. |
| Replay | PASS | All seven supported batches replay unchanged without removing later history. |
| Privacy | PASS | Tests use synthetic responses; existing private responses have zero hits in 817 tracked/unignored files. |
| Gate honesty | PASS | No Batch 6/7 outcome, T5-G2 completion, bundle freeze, CAR-T6 or RHB-T5 authorization is claimed. |

## Allowed claims

- The bounded T5-G2 paths for Batches 6 and 7 are implemented and verified.
- Morgan Super 3 has three and Mazda MX-5 Miata has two complete frozen-snapshot entries.
- Qualifying sequential decisions would move the state first to 18 exact / 2 reviewed and then to
  20 exact / 0 reviewed.
- The real state remains unchanged at 15 exact / 5 reviewed.

## Prohibited claims

- Either batch is already approved or materialized.
- One generic or reused response authorizes both batches.
- Snapshot-relative agreement is manufacturer-certified truth.
- Readiness completes T5-G2 or authorizes CAR-T5F, CAR-T6, RHB-T5 or model-quality claims.

## Verification record

Focused verification reported `26 passed`; the complete repository reported `1365 passed, 1
warning`. Focused Ruff, formatting, strict MyPy, compileall and diff checks passed. The only warning
was an existing Starlette/AnyIO deprecation. Real Batch 5 replay stayed unchanged, the real state
remained 15 exact / 5 reviewed, and the privacy scan found zero private-response hits.

This PASS applies only to implementation readiness and claim faithfulness. The two exact outcomes
remain separate owner decisions.
