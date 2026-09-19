# Local release casting owner decision 04 — evidence

Date: 2026-09-18. Lite / Lean Industrial. Verdict: **valid owner-scoped event; batch progress 4/5**.

The fourth event is checksum-bound to frozen packet
`189a3a69d6a580c6781876f79b52792617e996760cd65da379c861b1655bbb52`. It preserves the owner's exact
unprefixed response in the private ledger and records normalized decision `same_review_family`.
The event SHA-256 is
`dec834a797ed7d18f630f99195f1ae775f83e97b2684221f93d24d39ac1e6c36`.

The cumulative private ledger has SHA-256
`68065d88366150f8efe2027daee98f50f69ad7047907f0746e73ccb1244f280d`. Public evidence contains only
the ledger/packet hashes and aggregate 4-recorded/1-pending progress. It does not expose the question,
label, cluster ID, toy number, or verbatim answer.

The decision suite proves that only the next ordinal can be appended, earlier event bytes are
preserved, and duplicate, gap, response mismatch, checksum tamper, or summary tamper fails. Eleven
focused tests and the complete 660-test suite pass with only the existing Starlette/AnyIO
deprecation warning. Changed-file Ruff/format, strict MyPy, compileall, deterministic `--check`, and
`git diff --check` pass.

This evidence confirms review-level family grouping only. It does not merge releases, infer color,
promote a canonical product, write PostgreSQL, create evaluation labels, or change Dual RAG runtime.
