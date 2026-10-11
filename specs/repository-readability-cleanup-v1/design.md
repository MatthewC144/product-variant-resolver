# Repository Readability Cleanup v1 — Design

## Overview

The repository already contains substantial technical depth and immutable evidence. The problem is
the first reading path: the README mixes current results, historical experiments, governance
chronology, and release QA. This design changes presentation and navigation without changing the
resolver or its evidence.

## Information architecture

```text
README.md                          portfolio landing page (~150–250 lines)
    |
    +--> docs/README.md            technical index
            |
            +--> architecture/     system and component rationale
            +--> RESULTS.md        current, historical, and negative results
            +--> CODE-TOUR.md      active code reading path
            +--> LIMITATIONS.md    canonical human-readable limitations
            +--> ARTIFACT-POLICY.md
            +--> archive/README.md historical/governance entry
            +--> evidence/         immutable detailed proof
```

## Public claim model

- Primary category: Confidence-Aware Product Entity Resolution & Learning-to-Rank.
- Primary result: dual-source exact-release Top-1 `55% → 64%`.
- Primary denominator: 100 source observations from 50 held-out identities.
- Internal two-corpus wording: authority-separated dual-corpus retrieval.
- Human Knowledge: supporting review/explanation evidence; never identity authority.
- Runtime boundary: portfolio-grade research/engineering system, not a deployed marketplace
  service.

## Interfaces and data models

No API or persisted data contract changes. Documentation claim tests read the existing frozen
`raw-pointwise-final-test.json` and compare its aggregate metrics with the README. Link tests inspect
only the curated public reading path, not every immutable historical document.

## Active-core static repair

The static cleanup is limited to annotation/protocol correctness:

- modernize the forward annotation in `CalibrationArtifact.load`;
- mark the optional scikit-learn import with a precise `import-untyped` suppression because the
  dependency does not publish typing metadata;
- expose a stable version on `StructuredRetriever` so it satisfies the existing `Retriever`
  protocol.

These edits do not alter scores, candidate ordering, thresholds, or response semantics.

## Artifact handling

No large artifact is deleted or moved in this pass. The policy inventories retained checkpoints and
large reports, explains reconstruction/retention status, and makes Git LFS or release migration a
separate future decision. This avoids invalidating hashes and historical links during a readability
cleanup.

## Error handling

- Documentation tests fail if frozen headline metrics drift from the README.
- Link tests fail for missing relative targets in the curated public documentation set.
- Existing resolver tests remain the behavioral regression boundary.

## Testing strategy

1. Ruff and strict MyPy on the six active runtime modules.
2. New documentation claim/link tests.
3. Existing API/unit tests affected by the protocol annotation.
4. Existing measured-artifact tests updated to follow historical claims into `docs/RESULTS.md`.
5. `git diff --check` and a secret/tracked-local-file audit before commit.

## Security and privacy notes

No secrets, private row-level benchmark data, API keys, or local collection workspaces are added.
Documentation links point only to already tracked public artifacts.

## Decision

Prefer navigation and claim hierarchy over mass file movement. Moving historical modules or binary
artifacts would create broad hash/link churn with little first-read benefit and is therefore
deferred.

