# Serper dual-source runtime readiness v1 — Design

## Overview

Add a small deterministic audit module and one aggregate JSON artifact. The audit validates already
frozen metadata; it does not invoke retrieval, Pointwise inference, calibration or policy scoring.

## Architecture

```text
dual-source dataset + grouped split + development/final aggregates
                              |
legacy v2 policy + balanced aggregate
                              |
                    readiness validator
                              |
       ready only if source-matched development negatives
       and fresh positive/negative policy holdout both exist
                              |
                  aggregate readiness.json
```

## Interfaces

- `python -m product_variant_resolver.serper_dual_source_runtime_readiness --run`
  creates the artifact once after explicit readiness-only acknowledgement.
- `python -m product_variant_resolver.serper_dual_source_runtime_readiness --check`
  validates the immutable aggregate artifact.
- `build_readiness(root)` returns the deterministic in-memory payload for tests.

## Data model

The artifact contains frozen bindings, available reusable evidence, incompatible legacy evidence,
missing evidence, blockers, a minimum next-dataset contract and mutation guardrails. It contains no
row IDs, query text, identity answers, labels, candidates or predictions.

The minimum next dataset uses existing 100 positive development identities, adds 40 paired
catalog-relative no-match development identities, and reserves a fresh 20-positive/20-no-match
paired holdout. All 80 new identities must have one Image/Lens and one Shopping observation; the
fresh holdout must be frozen before resolver or policy access.

## Error handling

Any hash, schema, split, policy, result or aggregate drift raises an exception. Existing output
cannot be overwritten. Row-level keys in the output are rejected recursively.

## Security and privacy

No network call, API key or environment secret is required. The artifact contains only public
aggregate metadata already derivable from tracked evidence.

## Testing strategy

Tests verify the real artifact reproduces exactly, the blocked data counts and next contract are
correct, final/runtime guards remain false, mutated source hashes fail, and injected row-level fields
are rejected.

## Decision

Runtime integration code already exists and fails closed; the missing component is evidence, not
another runtime implementation. A readiness audit is therefore the smallest necessary next step.
It prevents the stronger dual-source ranking result from being incorrectly treated as calibrated
decision-policy evidence.
