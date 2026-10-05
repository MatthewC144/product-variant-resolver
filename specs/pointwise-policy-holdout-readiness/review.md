# Pointwise policy untouched-holdout readiness — QA review

Date: 2026-10-05. Mode: Lite / Lean Industrial. Verdict: **PASS — readiness logic; HOLD — data**.

## Requirement evidence

| Requirement | Evidence | Result |
|---|---|---|
| PPHR-R1 | v2 calibration, policy and selection hashes are bound; policy remains non-runtime. | PASS |
| PPHR-R2 | Three local sources were compared by case ID; only aggregate counts/hashes were saved. | PASS |
| PPHR-R3 | The only four untracked rows have zero human expected answers; eligible count is zero. | PASS |
| PPHR-R4 | One RHB no-match remains ineligible because split/scoring/evaluation are unauthorized. | PASS |
| PPHR-R5 | Artifact reports `holdout_not_ready`, 0 eligible, minimum 20 and shortfall 20. | PASS |
| PPHR-R6 | No external CSV or row-level query/label/case data was copied into the repository. | PASS |

## Finding

The resolver policy was not evaluated. Existing files do not provide an independent no-match test:
the useful 52 cases already selected v2 thresholds, while the other apparent rows are duplicates,
derivatives or unanswered exclusions. Reusing them would turn development-selection evidence into a
misleading test claim.

## Verification

Seven focused tests covering the new readiness artifact and its frozen v2 parent passed. Scoped
Ruff check/format, strict MyPy, compileall, CLI `--check` and `git diff --check` also passed. The
repository-wide suite has a pre-existing fail-closed baseline: 13 tests in
`tests/api/test_human_knowledge_storage_api.py` return 503 because the older v4 storage protocol
still binds a stale `retrieval.py` checksum. Repository-wide Ruff/MyPy likewise report historical
issues outside this change. Lite-mode acceptance therefore relies on the clean scoped checks and
records, rather than silently fixing or suppressing, those unrelated baselines.

## Next owner gate

Before any runtime discussion, authorize collection and independent adjudication of at least 20 new
organic queries whose expected families are absent from the same frozen 1,763-record catalog. Freeze
membership and answers before any resolver/model access. Do not synthesize negatives, reuse the 52
development rows or tune model/features/thresholds on the new holdout.
