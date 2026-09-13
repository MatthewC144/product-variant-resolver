# Human Knowledge v3 — Development AI Evaluation

Date: 2026-09-12. Mode: Lite. Engineering checkpoint PASS; development selection **FAIL**.
This applies the feature's HRR-R8–R11/R15 gates, not the canonical fixture rubric thresholds.
No final unseen v3 quality evaluation has occurred.

## Disclosure and raw evidence

The frozen pack contains 199 dev-only cases: 168 identity-derived positives (42 families × four
styles), 4 merge controls, 7 hold controls and 20 unrelated controls (10 opaque, 10 generic).
It is deliberately leaky and cannot establish independent accuracy. Selection never reads v1
queries/labels/benchmark/reports. The pre-output pack/manifest were not rewritten. Source hashes,
the unchanged grid, raw ordered candidate evidence and latency samples are retained in
[selection.json](../../../reports/family-retrieval-development-v1/selection.json), checksum
`dcc0cd4e09ec5b20862cfee39b90d65a12bbd48a80f7da29c0fbacb0da267853`.
The [readable grid](../../../reports/family-retrieval-development-v1/selection.md) shows all failures.

| Criterion | Observed across all 21 configurations | Verdict |
|---|---|---|
| Fixed selection grid | Seven floors × three weights; fixed 192-dimensional hashing, sparse/dense weights 1, RRF 60, Top-5 | PASS |
| Positive Recall@5 ≥0.90 | 164–168/168 = 0.9762–1.0000 | PASS |
| Every positive style Recall@5 ≥0.85 | Minimum 38/42 = 0.9048 | PASS |
| Merge Recall@5 =1 | 4/4 each | PASS |
| Forbidden family hits =0 | 0 each across merge/hold controls | PASS |
| Unrelated nonempty =0 | 10/20 each; all ten generic cases fail, opaque cases return empty | FAIL |
| Real-corpus p95 ≤25 ms | 29.370584–36.601250 ms | FAIL |
| Synthetic 3,000 p95 ≤150 ms | 337.150209–377.282500 ms | FAIL |
| Traceability and failure preservation | Raw metrics/cost recompute; winner null; freeze leaves runtime untouched | PASS |
| Canonical/debug authority | Existing isolation/default-debug/failure regressions pass | PASS |
| Independent final v2 holdout | Not authored; no qualifying committed artifact | NOT EVALUATED |

Real-corpus p50 is 8.512875–9.700000 ms. Recall@1 is 0.6905–0.9821 and MRR@5 is 0.8323–0.9911;
neither objective can select a safety/cost-failing candidate. There is no nearest-to-pass winner.

## Diagnosis supported by raw evidence

For `frd-unrelated-generic-00`, query `sealed blue collector model from storage box`, the highest
floor still returns provisional documents through `box`, `collector` and `blue`. All five returned
candidates have no character rank/score in that configuration. Thus this case's false suggestions
come through exact-token eligibility independent of the character floor; increasing that floor
cannot eliminate that admission path. This is a development diagnosis, not permission to modify
the frozen grid or rerun the old holdout.

The synthetic index has 2,431 posting keys and 419,820 posting entries, versus real 4,508 keys and
19,001 entries. Shared generic forms stress posting-derived comparisons; the observed cost failure
requires a new bounded-scoring design, not a claim that postings alone guarantee the budget.

## Cost honesty and verification

Host: macOS/Darwin arm64, processor arm, 10 logical CPUs, Python 3.12.13. One retrieval process,
K=5, `perf_counter_ns`, three warm-ups/configuration, 199 real samples/configuration, first 20
case-ID-ordered development queries for synthetic scale, nearest-rank percentiles. The desktop
was not an isolated benchmark host. Index construction, serialization, database, HTTP, network,
concurrent clients and production are excluded. Synthetic documents are not real catalog rows.
See the [fixed protocol](../human-knowledge-development-protocol.md).

Full suite: **236 passed**, no skips, one existing Starlette/AnyIO deprecation warning. Report JSON
arithmetic/source checks and Markdown byte checks pass. No-winner/overwrite protection, fixed grid,
no-v1-access, all safety/quality/cost rejection gates, tie-breaks and tamper rejection are covered.
Focused Ruff F/I and isolated strict MyPy for the two retrieval/selection modules pass. The old
v1 report reproduces unchanged; canonical fixture metrics and existing API/UI authority remain
unchanged. Full-repository lint/type debt is not claimed resolved.

## Decision

No v3 activation, no new final holdout, no PostgreSQL promotion and no actual 3,000-row expansion.
Return to Phase 1 for a new design decision addressing identity eligibility and scoring cost.
The current development FAIL remains immutable evidence; final quality requires a later newly
authored, owner-approved unseen holdout after a qualifying code/artifact freeze.
