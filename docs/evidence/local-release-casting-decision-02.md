# Local release casting owner decision 02 — evidence

Date: 2026-09-17. Lite / Lean Industrial. Verdict: **valid owner-scoped event; batch progress 2/5**.

The second event is checksum-bound to frozen packet
`189a3a69d6a580c6781876f79b52792617e996760cd65da379c861b1655bbb52`. It preserves the owner's exact
response, including the explicit question prefix, in the private ledger and records normalized
decision `same_review_family`. The event SHA-256 is
`81a2c413587125407ca5194a566f1f1cd70fe64f629d4cf7d89a218b353a21ac`.

The cumulative private ledger has SHA-256
`d58108f30c6ab38485312fe70eda6b2a7d03cb796ceb7f33faf27a46635c21d8`. Public evidence contains only
the ledger/packet hashes and aggregate 2-recorded/3-pending progress. It does not expose a question,
label, cluster ID, toy number, or verbatim answer.

Two new regression tests prove that a matching numeric prefix is accepted and preserved while a
mismatched prefix is rejected. The broader decision tests also prove ordered appends, exact
preservation of event 1, tamper rejection, bounded effects, and public privacy. Eleven focused tests
and the complete 660-test suite pass with only the existing Starlette/AnyIO deprecation warning.
Changed-file Ruff/format, strict MyPy, compileall, deterministic `--check`, and `git diff --check`
pass.

This evidence confirms review-level family grouping only. It does not merge releases, infer color,
promote a canonical product, write PostgreSQL, create evaluation labels, or change Dual RAG runtime.
