# Serper dual-source policy calibration v1 — Design

## Overview

Add one offline module that validates the two frozen datasets, creates a deterministic grouped
development split, scores only admitted development observations with the existing Pointwise path,
compares three calibrators and publishes aggregate-only development artifacts.

## Architecture

```text
100 positive development identities + 40 no-match development identities
                              |
                  grouped identity split (70/30 + 28/12)
                              |
                 frozen RRF Top-25 + generic Pointwise
                              |
          logistic / isotonic / temperature calibration fit
                              |
            selection metrics + deterministic method choice
                              |
               match / ambiguous / no_match thresholds
```

The 40 fresh holdout identities are validated as part of the frozen dataset contract but their
queries never enter the scoring iterator.

## Interfaces

- `python -m product_variant_resolver.serper_dual_source_policy_calibration --run`
  performs one development-only run and writes versioned aggregate artifacts.
- `python -m product_variant_resolver.serper_dual_source_policy_calibration --check`
  validates hashes, schemas, aggregate arithmetic and the runtime/final isolation contract.

## Data models

The input policy dataset contains 80 identities and 160 paired records. In-memory scoring rows carry
target ID, source type, grouped partition, truth, five ranking features and exact-Top-1 label. These
rows are never serialized. Public artifacts contain only calibrator parameters, frozen parent hashes,
partition counts, reliability aggregates, thresholds, shortfalls and guardrails.

## Error handling

Unknown fields, stale hashes, source-pair disagreement, wrong partition counts, missing catalog
bindings, candidate membership drift, non-finite metrics and infeasible decision gates fail closed.
Existing outputs are never overwritten.

## Security and privacy

The run performs no network requests and reads no API key. Query text and row-level predictions stay
in memory. The recursive artifact guard rejects row-level fields. The policy remains development-only.

## Testing strategy

Unit tests cover strict dataset validation, grouped split isolation, calibrator metrics and gate
shortfalls. Integration tests validate the real frozen artifacts, zero holdout scoring, deterministic
reproduction and unchanged runtime eligibility.

## Decision

Use the existing generic Pointwise winner rather than either rejected domain checkpoint. Compare
calibration methods because the measured bottleneck is confidence quality and coverage, not candidate
recall or another ranking architecture.

