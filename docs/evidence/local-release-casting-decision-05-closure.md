# Local release casting owner decision 05 and batch closure — evidence

Date: 2026-09-18. Lite / Lean Industrial. Verdict: **valid owner-scoped event; batch complete 5/5**.

The fifth event is checksum-bound to frozen packet
`189a3a69d6a580c6781876f79b52792617e996760cd65da379c861b1655bbb52`. It preserves the owner's exact
unprefixed response in the private ledger and records normalized decision `same_review_family`.
The event SHA-256 is
`5d4949550c43733dff2994408d73795e1dce960a8b80dca0ef9f5b7e00ee6872`.

The complete private ledger has SHA-256
`9da688295717588d553922f448e43b6a27255922bdd8513f3245247e39eaad4a`. Public evidence contains only
the ledger/packet hashes and aggregate 5-recorded/0-pending progress. It does not expose a question,
label, cluster ID, toy number, or verbatim answer.

The decision suite proves that all five ordinals occur exactly once, earlier event bytes are
preserved, status derives deterministically from event count, and duplicate, gap, response mismatch,
checksum tamper, or summary tamper fails. Eleven focused tests and the complete 660-test suite pass
with only the existing Starlette/AnyIO deprecation warning. Changed-file Ruff/format, strict MyPy,
compileall, deterministic `--check`, and `git diff --check` pass.

Closure proves that owner questions are answered, not that review relationships are materialized.
Canonical promotions, reviewed colors, PostgreSQL writes, evaluation labels, network requests, and
Dual RAG runtime changes remain zero. A new spec and explicit gate are required before any of them
can change.
