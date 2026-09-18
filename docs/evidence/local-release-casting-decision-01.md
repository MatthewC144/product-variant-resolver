# Local release casting owner decision 01 — evidence

Date: 2026-09-17. Lite / Lean Industrial. Verdict: **valid owner-scoped event; batch progress 1/5**.

The first event is checksum-bound to packet
`189a3a69d6a580c6781876f79b52792617e996760cd65da379c861b1655bbb52`, preserves the owner's exact
response in the private ledger, and records normalized decision `same_review_family`. The event's
interpretation is deliberately narrow: a review-level casting-family relationship is confirmed;
release variants, colors, synthetic catalog products, and canonical identities remain unapproved.

The cumulative private ledger has SHA-256
`89228cfa76982864d7cb983fd6a0652b117d7261fd83b47404bb8e98ee64db31`. Public evidence contains only
the ledger/packet hashes and aggregate 1-recorded/4-pending progress. It does not expose the question,
label, cluster ID, toy number, or verbatim answer.

Nine focused tests cover packet binding, verbatim normalization, sequential order, duplicate/gap
rejection, prior-event preservation, tamper rejection, public privacy, actual private ledger, and
committed aggregate progress. The full suite passes 658/658 with only the existing Starlette/AnyIO
deprecation warning. Changed-file Ruff/format, strict MyPy, compileall, deterministic `--check`, and
`git diff --check` pass.

The next step is question 2. No code or test result may infer its answer.
