# Serper dual-source runtime readiness v1 — Requirements

Date: 2026-10-10. Mode: Lite / Lean Industrial. Status: **approved by continue-next-step direction**.

## Goal

Determine whether the frozen dual-source Pointwise ranking evidence is sufficient to start policy
calibration or runtime activation. The audit must fail closed and must not score queries, fit a
model, select thresholds, reuse final-test answers or change runtime behavior.

## Observable requirements

- **SDSRR-R1 — Frozen input validation.** WHEN the audit runs, THE SYSTEM SHALL validate the hashes
  and contracts of the 150-target dual-source dataset, grouped split, development selection and
  one-shot ranking final artifact.
- **SDSRR-R2 — Existing policy validation.** WHEN legacy policy evidence is inspected, THE SYSTEM
  SHALL validate the frozen v2 calibration/policy and balanced holdout, and SHALL preserve
  `runtime_eligible=false`.
- **SDSRR-R3 — Distribution boundary.** WHEN readiness is reported, THE SYSTEM SHALL distinguish the
  new paired Image/Lens plus Shopping distribution from the older image-search/human no-match policy
  distribution and SHALL NOT claim the old policy is transferable.
- **SDSRR-R4 — Final-test isolation.** WHEN classifying reusable evidence, THE SYSTEM SHALL mark the
  50-target dual-source final as ranking evidence only and ineligible for fitting, threshold
  selection or a newly calibrated policy evaluation.
- **SDSRR-R5 — Data shortfall.** IF no source-matched dual-source no-match development set and no
  fresh positive/negative policy holdout exist, THEN THE SYSTEM SHALL return a blocked status and an
  explicit collection contract instead of calibrating or activating runtime.
- **SDSRR-R6 — Aggregate-only artifact.** WHEN the audit is materialized, THE SYSTEM SHALL save only
  hashes, counts, eligibility flags, blockers and the next action; it SHALL reject row-level query,
  identity, label, prediction or candidate fields.
- **SDSRR-R7 — No operational mutation.** WHILE the audit runs, THE SYSTEM SHALL load neither the
  neural model nor resolver and SHALL record zero scoring, fitting, threshold, API, secret and
  runtime changes.
- **SDSRR-R8 — Reproducibility.** WHEN `--check` runs, THE SYSTEM SHALL recompute the expected
  aggregate audit and fail if the tracked artifact differs.
