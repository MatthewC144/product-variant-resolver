# Local review-family anchored admission evaluation v2 — evidence

Date: 2026-09-21. Lite / Lean Industrial. Verdict: **FAIL; runtime integration blocked**.

Protocol SHA-256 `e3bb1b2f3fd92dfe06bc613e371448676af425cad5260e7f3acddd5f73add834`
bound the exact public `secondary-075` selection to the immutable v1 private query, benchmark, raw
result, scored result, projection, and public report before v2 policy scoring. The evaluation reused
the original 20 rows and executed zero retrieval calls; no v1 byte was overwritten.

The anchored policy admits source rank 1 and requires identity coverage at least 0.75 for ranks 2–5.
It preserves positive Recall@5 `1.0` (15/15), Recall@1 `0.8667` (13/15), family coverage `1.0` (5/5),
and zero retrieval/admission errors. It admits 26 of 44 source candidates and abstains from 18.

Hard-negative forbidden hits fall from the v1 baseline of three to two, but both remaining hits are
source rank 1. The precommitted gates require zero forbidden hits and zero forbidden rank-1 hits, so
the overall verdict is FAIL. Raising the secondary threshold cannot affect these anchored candidates
and was not attempted.

Private queries, labels, candidate identities, coverage, ranks, and case results remain under the
ignored owner-data tree. The committed report contains only hashes, aggregate counts/metrics/gates,
the fixed policy, limitations, and zero downstream effects. Ten focused and all 761 tests pass.
