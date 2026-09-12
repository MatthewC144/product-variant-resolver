# Family Retrieval Benchmark Contract — T48.1 Evidence

> Mode: Lite / Lean Industrial
>
> Status: PASS for T48.1 implementation scope
>
> Date: 2026-09-12

## What was verified

T48.1 implements the safety boundary that must exist before official holdout queries are written.
The builder has independent query-pack freeze/check, benchmark build/check, and project-owner label
validation paths. It calls no retriever and makes no network request.

The query validator requires exactly 105 test-only cases: 84 positives, 4 merges, 7 holds, and 10
unrelated controls. Every accepted family must have one `marketplace_noise` and one
`lexical_variation` case under the same group. All merge and hold registry entries must be covered,
and unrelated queries must have zero normalized-token overlap with all 142 Human Knowledge
documents. Duplicate IDs/queries, full casting phrases in lexical challenges, copied indexed or
human-label strings, unsupported noise tags, reordered cases, and any declaration that retrieval
output was viewed fail closed.

The frozen system-under-test block binds `human-knowledge-hybrid-v2`, `hashing-v1`, 192 dimensions,
RRF `k=60`, candidate limit 5, both catalog/projection versions and checksums, and the checksums of
`identity.py`, `retrieval.py`, and `human_knowledge.py`. This prevents a later code change from being
reported as though it were the same evaluation system.

The separate owner-decision validator requires all 105 case IDs exactly once, a project-owner role,
UTC timestamps, an approval and reason, type-correct expected identities or negative expectations,
and the exact frozen query-pack checksum. Merge labels must point to an existing human catalog
casting; holds and merges also carry forbidden duplicate family IDs. A changed query after approval
invalidates the decision artifact.

## Failure and reproducibility evidence

Six focused tests cover the valid composition, deterministic query-pack freeze, byte-reproducible
benchmark `--check`, copied/leaking queries, retained lexical phrases, unrelated token overlap,
viewed-output declarations, non-test use, excluded-use widening, system-version drift, partial or
duplicate decisions, stale checksums, and incorrect labels. Subprocess tests prefill outputs with
known-good sentinel text and confirm that invalid builds and stale check mode leave both files
unchanged.

Verification on 2026-09-12 produced:

- Focused benchmark-contract tests: `6/6 PASS`.
- Complete repository suite: `190/190 PASS` in 2.027 seconds on the final tree.
- Python compilation: PASS for `src`, `scripts`, and `tests`.
- Whitespace/diff check: PASS.
- Ruff: not available in this host environment, so no Ruff result is claimed.

The complete suite emitted only the already known, non-failing Starlette legacy-`httpx` environment
warning. No runtime source, canonical data, calibration/policy artifact, existing benchmark,
PostgreSQL state, official T48 query pack, owner label, or retrieval result changed.

## Gate and next action

T48.1 passes its acceptance boundary: invalid or incomplete input cannot produce or overwrite a
benchmark, while valid synthetic fixtures reproduce byte for byte. This does not measure retrieval
quality. T48.2 is next and must author the official 105 queries, run only the freeze/check path, and
commit their manifest before anyone views retrieval candidates, ranks, or scores.
