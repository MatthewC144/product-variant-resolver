# Portfolio release closure v1 — Design

## Overview

This is a verification-only milestone. It runs the repository's existing contracts and documents
their results; it does not introduce a new product flow or alter the current Dual-RAG, retrieval,
ranking, calibration or FastAPI architecture.

## Verification flow

```text
tracked checkout
   +--> full pytest regression
   +--> Ruff / strict MyPy / compileall / whitespace
   +--> frozen-data validators
   +--> in-process FastAPI health + three-state demonstration
   +--> tracked-secret and working-tree audit
                    |
                    +--> versioned QA review + Project Log + GitHub main
```

## Interfaces and data

No interface or data-model changes are permitted. The verifier uses the default offline app and
existing frozen datasets. Test caches and bytecode are local-only and remain ignored.

## Error handling

Any behavioral, data-integrity, API or active-runtime lint failure keeps the release verdict at
FAIL. A failure may be repaired only when it is a real implementation or test-contract defect
within this scope; model quality gates, frozen metrics and holdouts may not be weakened or rewritten
to make closure pass. Historical whole-repository lint/type findings are recorded as release debt
because bulk rewrites would invalidate source-hash-bound research evidence; they cannot be reported
as passing.

## Security notes

The hygiene audit inspects tracked filenames and tracked text for secret-like material and the known
owner-supplied Serper credential. It must not print environment values or read a local `.env`.

## Testing strategy

Use the repository's Python 3.12 virtual environment. Record exact denominators, static-analysis
debt and warnings in the QA review. The API demonstration is in-process and offline, so it does not
claim production networking, concurrency or deployment readiness.

## Decision

Prefer a bounded release audit over additional feature work. The strongest portfolio claim is a
reproducible, honestly scoped resolver—not an unverified runtime activation.
