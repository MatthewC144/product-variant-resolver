# AI eval evidence — Serper dual-source runtime readiness v1

Date: 2026-10-10. Scope: readiness only.
Artifact SHA-256: `d19fe5acdc1603eb7e0781c8e757f183c232efba1ad6f43d6d4aace168cc5364`.

| Dimension | Criterion | Observed | Verdict |
|---|---|---|---|
| Frozen bindings | Validate dataset, split, development/final ranking and legacy policy artifacts. | Seven SHA-256 bindings and their schemas validate. | PASS |
| Distribution validity | Do not transfer an older policy to Image/Lens plus Shopping without evidence. | `dual_source_transfer_validated=false`; status blocked. | PASS |
| Leakage control | Do not reuse the opened 50-target ranking final for a new policy. | Final is explicitly ineligible; final observations scored in this audit: 0. | PASS |
| Missing-class evidence | Require source-matched no-match development and fresh positive/negative holdout. | All three counts are zero and appear as blockers. | PASS |
| Output minimization | Persist aggregates only. | No query, target ID, identity, label, candidate or prediction fields. | PASS |
| Runtime boundary | No inference, fit, threshold, policy or activation work. | All guardrail counters/flags remain zero or false. | PASS |
| Reproducibility | Recompute exact expected artifact. | Focused tests and CLI `--check` pass. | PASS |

## Interpretation

This is a negative readiness result, not a model failure. It says the ranking layer has passed its
own final test while the decision layer lacks distribution-matched evidence. The correct response is
new data, not lowering the old threshold or treating Pointwise logits as confidence.

The required next collection is bounded to 80 new identities and 160 paired source observations.
That size is a minimum engineering Gate, not a claim of statistical representativeness or
production coverage.
