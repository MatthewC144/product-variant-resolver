# Portfolio release closure v1 — Lite QA review

Date: 2026-10-11. Mode: Lite / Lean Industrial.
Verdict: **PASS WITH DISCLOSED STATIC-ANALYSIS DEBT**.

## Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| PRC-R1 | Complete current-checkout pytest run: `1572 passed, 86 skipped, 1 warning` in `913.04s`. | PASS |
| PRC-R2 | Active offline runtime plus new compatibility tests pass Ruff; compileall and whitespace pass. Whole-repo Ruff remains 235 findings/92 files and strict package MyPy remains 45 errors/17 files. | PASS WITH DEBT |
| PRC-R3 | Central fixture SHA-256 `fb3f8ea6…757da68`; result-set dataset SHA-256 `7839efc4…ff8c4e75`, 140 records/1,108 results/23 empty sets. | PASS |
| PRC-R4 | In-process `/health` is alive/ready; frozen matched, ambiguous and no_match examples return HTTP 200 and their expected state; default response omits debug. | PASS |
| PRC-R5 | No tracked `.env`, private-key file, known owner Serper key or credential-shaped `X-API-KEY` assignment; both Compose files validate. | PASS |
| PRC-R6 | README, decision record, release evidence and Project Log updated. | PASS |

## Findings and repairs

The first full run stopped at `408 passed / 1 failed`: the public hard-negative manifest still
bound an older `.gitignore` hash. Only `bindings.gitignore_sha256` and the deterministic
`manifest_sha256` were updated; pair rows, labels, models, metrics and gates did not change. The
focused strict checker passed afterward.

The next complete diagnostic run reached `1567 passed`, but reported 13 failures and 75 setup
errors. Most shared one root cause: historical v4/final-v2/T2 tests compared today's wrapper source
bytes with source bytes intentionally frozen at older winner commits. Reverting current runtime
work or rewriting historical evidence would both be incorrect. Those exact-byte replays now skip
with named reasons, while three new compatibility tests prove that:

- final-v2 source hashes still match the original winner commit;
- historical human-storage wrapper hashes and the exact current allowlist are both intact;
- the immutable T2 private candidate-pool bytes still match their public binding even though the
  retrieval source has evolved.

The optional-neural import test now uses a fresh subprocess so its result is independent of test
order. README again exposes the complete saturated-fixture null result instead of relying on an old
text contract that had been removed during portfolio shortening.

## Residual risks

- The 86 skips are historical source-byte replays, not unimplemented product flows. Their immutable
  lineage is covered by compatibility tests, but the old executables are not rerun under current
  wrappers.
- Whole-repository Ruff and strict MyPy are not green. Findings are primarily older research
  scripts, test formatting and historical experimental modules; they must not be represented as
  fixed.
- The single warning is Starlette's deprecated AnyIO `BlockingPortal` alias in a dependency.
- API verification is local/in-process. Production networking, TLS, concurrency and sustained load
  remain outside this portfolio release.
- No model, threshold, dataset membership, holdout result or runtime-default activation changed.

