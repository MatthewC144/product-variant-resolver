# AI artifact evaluation — T5-G2 Batch 3 progress

Date: 2026-10-02
Scope: generated Batch 3 event, hash, state and progress claims
Verdict: **PASS — FAITHFUL THIRD-BATCH CLAIMS**

| Criterion | Result | Evidence and boundary |
|---|---|---|
| State accuracy | PASS | Exactly 9 candidates are approved exact, 11 remain reviewed and none are staged. |
| Authorization fidelity | PASS | A fresh Batch 3 authorization backs exactly three new attestations and events. |
| Field fidelity | PASS | Each event contains six agreeing fields; color/edition stay null and Zamac is context only. |
| Append integrity | PASS | All 26 prior events and 17 non-target candidate objects are preserved. |
| Link integrity | PASS | Ten authorization, 29 attestation and all 20 latest-event links validate. |
| Privacy | PASS | Three real owner responses have zero hits in 804 tracked/unignored text files. |
| Replay | PASS | Materialization returned `created`; two exact checks returned `unchanged`. |
| Gate honesty | PASS | No manufacturer truth, completed T5-G2, bundle freeze, CAR-T6 or RHB-T5 claim is made. |

## Allowed claims

- T5-G2 Batches 1–3 contain nine output-blind, owner-authorized exact events.
- The three Subaru BRZ records agree with six fields in the frozen community snapshot.
- T5-G2 remains in progress with 11 candidates still reviewed.
- Batches 1–2 and all other pre-existing history were preserved.

## Prohibited claims

- The nine records are manufacturer-certified truth.
- Zamac or color-context text proves a color or edition.
- T5-G2, CAR-T5F or the authority bundle is complete.
- This decision authorizes CAR-T6, RHB-T5 or measures resolver/RAG quality.

## Verification record

Pre-materialization verification reported focused `18 passed` and full-repository `1357 passed, 1
warning`, with Ruff, formatting, strict MyPy, compileall and diff checks passing. Post-materialization
verification covered 18 focused tests, two unchanged replays, old-object preservation, all hash
links, permissions, ignore rules, forbidden-bundle absence, field boundaries and a zero-hit privacy
scan. The full suite was not rerun after the state-only append.

This PASS applies only to the integrity and faithfulness of T5-G2 Batch 3. Later exact outcomes,
bundle freezing, RHB-T4 re-audit, RHB-T5 and model quality remain unverified or unauthorized.
