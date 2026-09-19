# Local release casting review-family materialization — evidence

Date: 2026-09-18. Lite / Lean Industrial. Verdict: **PASS for private review-layer materialization**.

The complete decision ledger
`9da688295717588d553922f448e43b6a27255922bdd8513f3245247e39eaad4a` deterministically produces a
private registry with SHA-256
`1b8c18618390c4f224634da7a0fe3ee403c2c49f7e1614b941e4332196fc1a83`. It contains five owner-confirmed
review relationships and 18 unique source references. Every release reference remains
`held_for_variant_review`; no candidate identity is selected.

The first CLI run returned `created`, the exact second run returned `unchanged`, and `--check`
returned `valid` with the same registry hash. Tests also prove that a conflicting existing byte,
partial output pair, incomplete ledger, changed summary/checksum, duplicate source, duplicate review
cluster, or widened decision fails closed. A simulated second-directory write failure removes the
newly created first directory.

The complete registry remains under the gitignored local data tree. Its committed public manifest
contains only input/output hashes and aggregate 5/18/0 counts; privacy checks find no labels, cluster
IDs, source IDs, toy numbers, or verbatim owner answers.

Thirteen focused tests and the complete 673-test suite pass. Ruff F/I and format, strict MyPy,
compileall, installed CLI checks, deterministic artifact verification, and `git diff --check` pass.
The only warning is the existing Starlette/AnyIO deprecation notice.

Canonical promotions, reviewed colors, PostgreSQL writes, evaluation labels, network requests, and
runtime-indexed relationships are all zero. This artifact is not yet part of either Dual RAG corpus.
