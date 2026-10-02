# AI artifact evaluation — T5-G2 Batch 1 progress

Date: 2026-10-01
Scope: generated second-Gate events, hashes and progress claims for one three-entry family batch
Verdict: **PASS — FAITHFUL PARTIAL EXACT-AUTHORITY CLAIMS**

This rubric checks whether the Batch 1 append records only the independently authorized transition,
preserves first-Gate history, protects private owner text and avoids claiming a completed authority
bundle or benchmark authorization.

| Criterion | Result | Evidence and boundary |
|---|---|---|
| State accuracy | PASS | Exactly 3 entries are `approved_exact`; 17 remain `reviewed` and zero are staged. |
| Fresh authorization | PASS | The T5-G2 response hash differs from and explicitly links to the corresponding prior-Gate hash. |
| Field fidelity | PASS | Each exact event contains the six supported, agreeing snapshot fields; color and edition remain null. |
| Append integrity | PASS | All 20 earlier T5-G1 events and all 17 non-batch candidate objects are byte/object-equivalent. |
| Link integrity | PASS | Eight batch authorization hashes, 23 attestation hashes and all 20 candidate latest-event links validate. |
| Privacy | PASS | The owner response occurs zero times across 796 tracked/unignored text files; private ledgers remain ignored with restrictive permissions. |
| Replay | PASS | Materialization returned `created`; two exact `--check` runs returned `unchanged`. |
| Gate honesty | PASS | Exactness is community-snapshot-relative; no authority bundle, CAR-T5F, CAR-T6 or RHB-T5 claim is made. |

## Allowed claims

- T5-G2 Batch 1 contains three output-blind, owner-authorized `reviewed -> approved_exact` events.
- The three records agree with the six named fields in the frozen community snapshot.
- T5-G2 remains in progress, with 17 candidates still at `reviewed`.
- Earlier first-Gate history and non-batch candidate states are preserved.

## Prohibited claims

- The three records are Mattel/manufacturer-certified truth.
- T5-G2 or CAR-T5 is complete, or an authority bundle has been frozen.
- Color, edition or free-text variant context was approved as exact evidence.
- This decision authorizes CAR-T5F, CAR-T6, RHB-T5, or measures resolver/RAG quality.

## Verification record

Before real state materialization, T5-G2 focused tests reported `12 passed`, T5-G1 regression
reported `71 passed`, and the full repository reported `1351 passed, 1 warning`. Ruff, formatting,
strict MyPy, compileall and diff checks passed. The only warning was an existing Starlette/AnyIO
deprecation.

After materialization, checks covered fresh cross-Gate response hashes, complete event/attestation/
authorization links, old-object preservation, six-field evidence, permission and ignore boundaries,
forbidden bundle absence, two unchanged replays and the zero-hit privacy scan. The full suite was not
rerun after the state-only write.

The PASS applies only to the faithfulness and integrity of this partial T5-G2 append. Remaining
exact outcomes, bundle freezing, RHB-T4 re-audit, RHB-T5 and model quality remain unverified or
unauthorized.
