# AI eval evidence — Serper dual-source policy calibration v1

Date: 2026-10-11. Scope: development-only calibration and selective prediction.
Selection artifact SHA-256:
`11caad121fa32a006abdc7cb08e8138a651bfcea5f76837471268fd65cee14e6`.

| Dimension | Criterion | Observed | Verdict |
|---|---|---|---|
| Frozen inputs | Bind catalog, positive/no-match data, development ranking and model manifest. | Six SHA-256 bindings validate. | PASS |
| Leakage control | Keep both sources per identity together and leave all 40 fresh holdout identities unopened. | 98/42 fit/selection identities; holdout observations scored `0`. | PASS |
| Method comparison | Compare three predeclared calibration families on the same rows. | Logistic, isotonic and temperature evaluated on 196 fit / 84 selection observations. | PASS |
| Calibration quality | Select lowest Brier, then NLL, ECE and stable name. | Logistic wins: Brier `0.190535`, NLL `0.566745`, ECE `0.184484`. | PASS |
| Selective match Gate | At least 5 accepted observations with exact precision at least `0.90`. | No feasible threshold. | FAIL |
| No-match Gate | At least 5 no-match decisions at precision at least `0.90` and false-no-match at most `0.10`. | Not evaluated because the match Gate failed. | NOT EVALUATED |
| Output minimization | Publish no query, identity, label, score or prediction rows. | Only parameters and aggregate metrics are tracked. | PASS |
| Runtime boundary | No policy or runtime activation after a failed Gate. | `policy_path=null`; runtime flags remain false. | PASS |

## Interpretation

Calibration improved the measurement of uncertainty but did not create a safe operating point.
Among catalog-present selection observations, Shopping is materially stronger than Image/Lens
(`21/30` versus `8/30` exact Top-1), which makes a single cross-source threshold particularly weak.
Calibration is confidence mapping; it cannot turn an incorrect Top-1 release into the correct release.

This artifact therefore supports two claims only: the project implements a reproducible calibration
comparison, and its safety Gate correctly rejects the resulting policy. It does not support a
runtime-quality claim, a manufacturer/global truth claim, or opening the fresh holdout.

## Recommended development follow-up

Use development data only to audit Image/Lens failure modes and decide prospectively whether the
next version tests source-conditional calibration or improves ranking evidence. Do not lower the
90% precision Gate after seeing this result, and do not use the sealed holdout for method choice.
