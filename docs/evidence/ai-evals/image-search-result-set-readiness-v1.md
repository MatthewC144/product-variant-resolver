# AI eval evidence — image-search result-set readiness v1

Date: 2026-10-11. Scope: product-boundary and data-readiness audit only.
Status: **dataset ready; aggregation and resolver scoring not yet evaluated**.

Dataset SHA-256:
`7839efc44ced91fe4ae885b7d3019c8d442fcf262fce73470713df52ff8c4e75`.

| Dimension | Criterion | Observed | Verdict |
|---|---|---|---|
| Product boundary | Model the evidence between livestream screenshot search and pricing lookup. | Predecessor path is frame → Serper Lens → up to 10 titles → candidate consensus → pricing keyword. | PASS |
| Current benchmark gap | Distinguish single-title ranking from full result-set resolution. | Current 150-target benchmark stores one Image/Lens title per identity. | PASS |
| Legacy evidence | Reuse prior data only within its label authority. | 101 identity labels: 95 Hot Wheels; 85 Hot Wheels cases retain 2–3 candidates; labels are primarily casting-level. | PASS |
| Full-identity safety | Do not infer exact releases from casting-only legacy labels. | Legacy candidates are not promoted to complete release truth. | PASS |
| New frozen membership | Use development identities only. | Contract binds 100 positive plus 40 no-match development identities; all policy/ranking holdouts excluded. | PASS |
| Final schema | Preserve ordered raw/cleaned hits and complete expected identity without operational metadata. | Strict Pydantic contract and seven focused tests pass. | PASS |
| Live collection | Obtain up to ten Lens titles for every frozen identity. | 140/140 identities retained; 1,108 title hits; 23 empty sets preserved. | PASS |
| Aggregation/scoring | Compare top-title, deterministic consensus and learned aggregation. | Dataset exists, but no result-set resolver output has been evaluated. | NOT EVALUATED |
| Runtime boundary | Do not change `/resolve`, pricing calls or policy behavior. | Runtime changes: `0`. | PASS |

## Interpretation

The existing ranking and calibration evidence answers whether one noisy title maps to a catalog
release. It does not yet answer the original FlipRadar question: how multiple reverse-image-search
results should be combined before price lookup. The next dataset must retain the ordered result set
instead of only the provider's first or locally selected title.

The predecessor data is useful for casting-level candidate-selection analysis, but most rows do not
contain authority-backed toy identifiers or full release fields. Treating those labels as exact
release truth would manufacture ground truth. The new contract therefore derives complete answers
only from the already frozen catalog-backed development identities.

## Dataset profile

Of 100 catalog-present development records, 79 have at least one result and 21 are empty. Of 40
catalog-relative no-match records, 38 have results and two are empty. Result-set sizes are 23×0,
6×3, 5×6 and 106×10. Conservative cleaning changes 609/1,108 titles while retaining the raw value.

Across all records, 117 result sets contain at least 80% of expected casting tokens, 60 contain the
toy identifier, 113 contain the release year, and 60 contain casting, year and toy-number evidence
together. These are data-profile counts, not resolver accuracy.

## Next permitted experiment

Use only these 140 development identities to compare top-title versus multi-title evidence fusion.
Do not open the existing fresh 40-target policy holdout, call a pricing API, or claim screenshot-level
accuracy until an independent full-pipeline holdout exists.
