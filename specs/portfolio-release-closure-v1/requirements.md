# Portfolio release closure v1 — Requirements

Date: 2026-10-11. Mode: Lite / Lean Industrial. Status: confirmed for execution.

## Goal

Close the portfolio release without changing the resolver architecture, model, datasets,
thresholds or runtime policy. The closure proves that the checked-in project is reproducible,
safe to publish and demonstrable through its existing title-to-identity FastAPI boundary.

## Observable requirements

- **PRC-R1 — Full regression.** WHEN the release is verified, THE SYSTEM SHALL complete the entire
  tracked pytest suite with no failures.
- **PRC-R2 — Static quality and debt disclosure.** WHEN source and test code are checked, THE
  SYSTEM SHALL pass Ruff for the active offline runtime path, Python bytecode compilation and
  `git diff --check`; whole-repository Ruff and strict MyPy SHALL be executed and any pre-existing
  findings SHALL be counted and disclosed rather than bulk-rewriting hash-bound research sources.
- **PRC-R3 — Frozen-data integrity.** WHEN tracked datasets are checked, THE SYSTEM SHALL pass the
  central fixture validator and the current image-search result-set validator without rewriting
  any frozen artifact.
- **PRC-R4 — Demonstrable API.** WHEN the default offline FastAPI application is exercised, THE
  SYSTEM SHALL report healthy readiness and demonstrate `matched`, `ambiguous` and `no_match`
  responses while keeping bounded debug data opt-in.
- **PRC-R5 — Publication hygiene.** WHEN the tracked repository is audited, THE SYSTEM SHALL contain
  no committed local environment file, private key or known user-supplied API credential, and the
  working tree SHALL contain no unintended release artifact.
- **PRC-R6 — Evidence closure.** WHEN all checks finish, THE SYSTEM SHALL publish a versioned QA
  review and Project Log entry that distinguish verified behavior from still-blocked model/runtime
  claims.
