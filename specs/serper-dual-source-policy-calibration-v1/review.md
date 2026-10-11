# Serper dual-source policy calibration v1 — Lite QA review

Date: 2026-10-11. Mode: Lite / Lean Industrial.
Verdict: **PASS — the development experiment is valid; policy qualification is a shortfall**.

Selection artifact SHA-256:
`11caad121fa32a006abdc7cb08e8138a651bfcea5f76837471268fd65cee14e6`.

## Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| SDSPC-R1 | All catalog, dataset, split, ranker-selection and model-manifest hashes are pinned and checked. | PASS |
| SDSPC-R2 | The identity-grouped split contains 70/30 positive and 28/12 no-match fit/selection identities; paired sources never split. | PASS |
| SDSPC-R3 | Fresh 40-target holdout observations scored: `0`; opened ranking-final reused: `false`. | PASS |
| SDSPC-R4 | The existing raw RRF Top-25 plus pinned generic MiniLM Pointwise scorer is reused without refitting. | PASS |
| SDSPC-R5 | Logistic, isotonic and temperature methods are compared by the frozen Brier/NLL/ECE rule. | PASS |
| SDSPC-R6 | Brier, NLL, ECE, reliability, risk/coverage and source aggregates are stored without row-level outputs. | PASS |
| SDSPC-R7 | The 90%-precision match Gate cannot accept five observations; a shortfall and no policy are published. | PASS |
| SDSPC-R8 | No runtime default changed; `runtime_eligible=false`. | PASS |

## Measured result

Five-feature logistic calibration won with Brier `0.190535`, NLL `0.566745`, ECE `0.184484`
and AURC `0.479008` on 84 selection observations. Isotonic had a lower ECE (`0.115455`) but a
worse Brier score (`0.208026`), so it did not win under the preregistered rule. Temperature scaling
was worse on all four headline measures.

The selected confidence cannot produce at least five accepted matches at 90% exact precision.
Consequently, no match threshold is admitted, the no-match threshold is not evaluated in isolation,
and no `policy.json` exists. This is a valid fail-closed result, not a passing runtime policy.

The source breakdown explains much of the limitation: among the 30 catalog-present selection
observations per source, exact Top-1 is `8/30` for Image/Lens and `21/30` for Shopping. The remaining
12 observations per source are no-match cases. A single confidence map cannot repair incorrect
candidate ordering, especially for Image/Lens.

## Verification

- Focused and adjacent evaluation tests: `29 passed`.
- Ruff and Ruff format: PASS.
- strict MyPy for the new implementation and tests: PASS.
- Artifact CLI `--check`: PASS.
- Row-level-output guard, holdout isolation and runtime boundary: PASS.

## Next permitted action

Do not open the fresh holdout. The next development task should diagnose source-specific ranking
errors and predeclare either source-conditional decision policies or a ranking-data remediation.
Any changed method needs a new development version and must keep this holdout sealed.
