# Local release casting owner decision 03 — evidence

Date: 2026-09-17. Lite / Lean Industrial. Verdict: **valid owner-scoped event; batch progress 3/5**.

The third event is checksum-bound to frozen packet
`189a3a69d6a580c6781876f79b52792617e996760cd65da379c861b1655bbb52`. It preserves the owner's exact
unprefixed response in the private ledger and records normalized decision `same_review_family`.
The event SHA-256 is
`256bd8d3ca1768ba20de8e12193463d0e871f6ca78aa14cdc1799d11d36c3d36`.

The cumulative private ledger has SHA-256
`92be88b06461e5bac0e8086edae8795e8a151829402f0cdd5f0cdbad8eedf419`. Public evidence contains only
the ledger/packet hashes and aggregate 3-recorded/2-pending progress. It does not expose the question,
label, cluster ID, toy number, or verbatim answer.

The existing decision suite proves that only the next ordinal can be appended, earlier event bytes
are preserved, and duplicate, gap, response mismatch, checksum tamper, or summary tamper fails.
Eleven focused tests and the complete 660-test suite pass with only the existing Starlette/AnyIO
deprecation warning. Changed-file Ruff/format, strict MyPy, compileall, deterministic `--check`, and
`git diff --check` pass.

This evidence confirms review-level family grouping only. It does not merge releases, infer color,
promote a canonical product, write PostgreSQL, create evaluation labels, or change Dual RAG runtime.
