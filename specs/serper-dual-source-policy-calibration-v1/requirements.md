# Serper dual-source policy calibration v1 — Requirements

Date: 2026-10-11. Mode: Lite / Lean Industrial. Status: approved by continue-next-step direction.

## Goal

Fit and select a development-only three-state decision policy for the frozen paired Image/Lens and
Shopping distribution. Reuse the frozen generic MiniLM Pointwise ranker, score only development
records, compare predeclared calibration methods, and keep the fresh policy holdout sealed.

## Observable requirements

- **SDSPC-R1 — Frozen inputs.** WHEN calibration starts, THE SYSTEM SHALL validate the 150-target
  positive dataset, its 100-target development split, the 80-target policy dataset, the 1,763-row
  catalog and the pinned Pointwise model by SHA-256 before scoring.
- **SDSPC-R2 — Grouped development partition.** WHEN fit/selection partitions are derived, THE
  SYSTEM SHALL keep both source observations for one identity together and assign exactly 70/30
  positive identities and 28/12 no-match identities to fit/selection.
- **SDSPC-R3 — Holdout isolation.** WHILE development calibration runs, THE SYSTEM SHALL score zero
  records from the 20-positive/20-no-match policy holdout and SHALL NOT use the opened 50-target
  ranking final for fitting, method selection or threshold selection.
- **SDSPC-R4 — Fixed ranking path.** WHEN a development observation is scored, THE SYSTEM SHALL use
  the frozen raw query, RRF Top-25 pool and pinned generic MiniLM Pointwise reranker without changing
  candidate membership, model weights or features.
- **SDSPC-R5 — Predeclared calibration comparison.** WHEN calibration is fitted, THE SYSTEM SHALL
  compare five-feature logistic calibration, top-score isotonic regression and top-score
  temperature scaling on identical fit/selection observations, selecting lowest Brier score then
  NLL, ECE and stable method name.
- **SDSPC-R6 — Reliability evidence.** WHEN methods are compared, THE SYSTEM SHALL report Brier,
  NLL, fixed ten-bin ECE, reliability bins, risk/coverage points and source-specific aggregate
  metrics without persisting row-level queries, identities, labels, scores or predictions.
- **SDSPC-R7 — Three-state gates.** WHEN thresholds are selected, THE SYSTEM SHALL require at least
  five accepted matches at at least 90% exact precision, and at least five no-match decisions at at
  least 90% no-match precision with at most 10% false-no-match rate on catalog-present selection
  observations. IF either gate fails, THE SYSTEM SHALL publish a shortfall and no policy.
- **SDSPC-R8 — Runtime boundary.** WHEN a policy is materialized, it SHALL remain
  `runtime_eligible=false`; the FastAPI default, runtime package and final holdout SHALL remain
  unchanged.

