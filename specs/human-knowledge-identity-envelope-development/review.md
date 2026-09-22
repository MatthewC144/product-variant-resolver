# QA review — Human Knowledge query-global identity envelope v2

Date: 2026-09-22. Verdict: **implementation PASS; historical eligibility FAIL; holdout NOT RUN**.

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| HIE-R1 | Calibration source map contains only committed public corpus/artifacts; private-local reads are false | PASS |
| HIE-R2 | HIC-v1 source hash remains `167c03...825f`; no v1 artifact was edited | PASS |
| HIE-R3 | The required 16+16 holdout was intentionally not materialized because HIE-T3 failed before protocol freeze | NOT RUN / BLOCKED |
| HIE-R4 | Every evaluated candidate receives the same per-query envelope checksum; candidate-specific span selection is absent | PASS |
| HIE-R5–R6 | Conserved digit/model frames and the structural `88`/`1988` year-suffix rule have focused tests; `R33`/`R34`, `R33`/`BNR34`, and `M2`/`M4` remain conflicts | PASS |
| HIE-R7 | Decision evidence uses normalized query plus casting/approved aliases; no release/color/series/private label is used | PASS |
| HIE-R8 | Five ordered categorical policies and the fixed 0.75 secondary gate are implemented without a new scalar threshold | PASS |
| HIE-R9 | Existing 223, v4 22, and HIC-v1 24 rows were rescored with zero retrieval; new 32-case retrieval was blocked before protocol | PASS for historical phase; new phase NOT RUN |
| HIE-R10 | Candidate evaluations record envelope, identity form, alignments, numeric state, residuals, reason codes, and decision | PASS |
| HIE-R11 | No non-reference policy preserved every historical positive while reaching zero negatives | FAIL |
| HIE-R12 | Deterministic output is `historical_calibration_fail`, zero survivors, `winner: null`, and no downstream authorization | PASS |
| HIE-R13 | Repeated freeze returns `calibration_failed_unchanged`; repeated `--check` recomputes valid identical evidence | PASS |
| HIE-R14 | API, Dual RAG runtime, PostgreSQL, canonical identity, release promotion, and physical features are unchanged | PASS |

## Findings

Implementation integrity passes. The query-global envelope, numeric conservation, five policies,
historical rescoring, phased CLI, and fail-closed validators behave deterministically. Twenty-five
focused tests, 77 related tests, and all 813 repository tests pass. The full suite has one existing
Starlette/AnyIO deprecation warning.

Historical product eligibility fails. The reference policy preserves all required positives but
leaves 11/12 v4 and 10/12 HIC-v1 absent identities nonempty. The closest safety policy,
`envelope-bilateral`, reduces each negative set to 1/12 but preserves only 146/168 existing,
9/10 v4, and 10/12 HIC-v1 positives. No non-reference policy satisfies every exact gate.

The historical failure was persisted before any new holdout or retrieval. Repeating
`--freeze-protocol` produces `calibration_failed_unchanged`; no protocol, pack, raw artifact, or
selection exists. The frozen development source SHA-256 is
`c91d8e253f1cd19cf59b626e794673defe2e28aea6c993cbce350d1698e83a5e`.

Targeted Ruff/format, targeted MyPy, compileall, CLI integrity, artifact hashes, and
`git diff --check` pass. Repository-wide formatting and MyPy are not clean: Ruff reports 83 legacy
files that would be reformatted, and MyPy reports 51 existing/cross-module issues, including one
full-graph inference error at the frozen HIE `QueryEnvelope.text` construction. This closure does
not rewrite frozen source after observing the result; the debt must be handled in a separate
versioned maintenance task.

## Carry forward

Do not execute HIE-T4–T7's conditional holdout branch, another private evaluation, or runtime
integration. Archive and publish this null result as evidence that historical calibration prevented
32 unnecessary retrieval calls. A new technical attempt requires a v3 specification and a new
source/evidence namespace. Repository-wide formatting and type cleanup must remain behavior-neutral
and separate from the frozen v2 experiment.
