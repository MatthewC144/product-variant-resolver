# Human Knowledge anchored compatibility admission v3 — evidence

Date: 2026-09-20. Lite / Lean Industrial. Verdict: **public-development PASS; private gate pending**.

Protocol SHA-256 `0168cce9bbaa8206eb9f1c4a2a9dbde3d6025cc7bc5cf83a00742c0a1356857c`
froze the upstream v2 report hash, rank-1 anchor, eight secondary thresholds, recall/governance gates,
and winner ordering before v3 scoring. The experiment reused 223 validated public-development raw
pools and executed zero retrieval calls. No private projection or final-evaluation artifact was read.

| Secondary coverage | Eligible | Old R@5 | New required | Forbidden cases | Admitted / source |
|---:|---:|---:|---:|---:|---:|
| 0 | yes | 168/168 | 24/24 | 18/24 | 329/329 |
| 1/3 | yes | 168/168 | 24/24 | 16/24 | 316/329 |
| 0.4 | yes | 168/168 | 24/24 | 8/24 | 282/329 |
| 0.5 | yes | 168/168 | 24/24 | 7/24 | 274/329 |
| 0.6 | yes | 168/168 | 24/24 | 2/24 | 237/329 |
| 2/3 | yes | 168/168 | 24/24 | 2/24 | 234/329 |
| 0.75 | yes | 168/168 | 24/24 | 0/24 | 212/329 |
| 1.0 | no | 167/168 | 24/24 | 0/24 | 209/329 |

The frozen rule selects `secondary-075`: always retain source rank 1, retain ranks 2–5 only at
identity-token coverage at least 0.75, and preserve source order. It abstains from 117 secondary
candidates while keeping every required development target. Its status is explicitly
`qualified_for_new_private_shadow_evaluation_only`.

Selection JSON SHA-256 is
`664ec742353fbb1793a28494a0aec7046511b29b98bf594192c37f468fd4c93d`. This result does not prove
general accuracy and may still preserve a wrong rank-1 candidate. The immutable private evaluation
was not opened or rerun. API, runtime retriever, PostgreSQL, canonical catalog, and Dual RAG behavior
remain unchanged. Twelve focused and all 751 repository tests pass.
