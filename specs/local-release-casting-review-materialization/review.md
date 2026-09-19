# Local release casting review-family materialization — QA review

Date: 2026-09-18. Mode: Lite / Lean Industrial. Verdict: **PASS**.

## Coverage

| Requirement | Result | Evidence |
|---|---|---|
| LRFM-R1 | PASS | Incomplete and checksum-tampered ledgers are rejected; real complete ledger validates. |
| LRFM-R2–R3 | PASS | Affirmative decisions create relationships; `keep_separate` and `unknown` create non-materialized exclusions. |
| LRFM-R4 | PASS | Source references remain distinct/held; duplicate source or cluster assignment fails. |
| LRFM-R5–R6 | PASS | Candidate evidence is context-only; canonical/color/SQL/evaluation/runtime effects stay zero. |
| LRFM-R7 | PASS | Repeated builds produce identical IDs, item hashes, registry SHA, manifest, and report. |
| LRFM-R8 | PASS | First run is `created`, exact rerun is `unchanged`, conflicting bytes and partial state fail closed. |
| LRFM-R9 | PASS | Simulated public-write failure removes the newly created private directory and leaves no partial pair. |
| LRFM-R10 | PASS | Registry is gitignored; public privacy tests reject labels, clusters, source IDs, toy numbers, and answers. |
| LRFM-R11 | PASS | Real output reports 5 relationships, 18 held references, 0 exclusions, and all downstream effects zero. |

## Verification

Thirteen focused tests and the complete 673-test repository suite pass. Changed-file Ruff F/I and
format, strict MyPy, compileall, installed CLI create/unchanged/check behavior, deterministic artifact
check, privacy scan, and `git diff --check` pass. The full suite emits only the existing
Starlette/AnyIO deprecation warning.

## Remaining boundary

This registry is a review-layer artifact, not a canonical catalog or retrieval corpus. PostgreSQL
ingestion, evaluation labels, Dual RAG indexing, release-variant adjudication, and color enrichment
remain separate future gates.
