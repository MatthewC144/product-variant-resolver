# AI artifact evaluation — T5-G2 Batch 4 progress

Date: 2026-10-02
Scope: generated Batch 4 event, hash, state and progress claims
Verdict: **PASS — FAITHFUL FOURTH-BATCH CLAIMS**

| Criterion | Result | Evidence and boundary |
|---|---|---|
| State accuracy | PASS | Exactly 12 candidates are approved exact, 8 remain reviewed and none are staged. |
| Authorization fidelity | PASS | A fresh Batch 4 authorization backs exactly three new attestations and events. |
| Field fidelity | PASS | Each event contains six agreeing fields; color/edition stay null and color wording is context only. |
| Append integrity | PASS | All 29 prior events and 17 non-target candidate objects are preserved. |
| Link integrity | PASS | Eleven authorization, 32 attestation and all 20 latest-event links validate. |
| Privacy | PASS | Four real owner responses have zero hits in 811 tracked/unignored text files. |
| Replay | PASS | Materialization returned `created`; two correctly scoped exact checks returned `unchanged`. |
| Gate honesty | PASS | No manufacturer truth, completed T5-G2, bundle freeze, CAR-T6 or RHB-T5 claim is made. |

## Allowed claims

- T5-G2 Batches 1–4 contain 12 output-blind, owner-authorized exact events.
- The three Nissan Skyline records agree with six fields in the frozen community snapshot.
- T5-G2 remains in progress with eight candidates still reviewed.
- Batches 1–3 and all other pre-existing history were preserved.

## Prohibited claims

- The 12 records are manufacturer-certified truth.
- Color-context text proves a color or edition.
- T5-G2, CAR-T5F or the authority bundle is complete.
- This decision authorizes CAR-T6, RHB-T5 or measures resolver/RAG quality.

## Verification record

Pre-materialization verification reported focused `20 passed` and full-repository `1359 passed, 1
warning`, with Ruff, formatting, strict MyPy, compileall and diff checks passing. Post-materialization
verification covered 20 focused tests, two unchanged replays, old-object preservation, all hash
links, permissions, ignore rules, forbidden-bundle absence, field boundaries and a zero-hit privacy
scan. One incorrectly cross-Gate operator replay failed before writing, as required. The full suite
was not rerun after the state-only append.

This PASS applies only to the integrity and faithfulness of T5-G2 Batch 4. Later exact outcomes,
bundle freezing, RHB-T4 re-audit, RHB-T5 and model quality remain unverified or unauthorized.
