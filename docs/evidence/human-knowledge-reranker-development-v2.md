# Human Knowledge candidate-relative reranker v2 — evidence

Date: 2026-09-20. Lite / Lean Industrial. Verdict: **experiment valid; no mitigation qualified**.

Protocol SHA-256 `fe57cd3b17795142f7b1f74445a95d3c39c7e9598093308d919ffd1285fe01e7`
froze a 25-candidate pool, Top-5 output, the candidate-relative formula, seven penalty weights,
recall/governance gates, and deterministic ordering before retrieval. Inputs are the committed
142-document corpus, 199-case development pack, and 24-case safety pack. No private local projection
or final-evaluation artifact was read.

The v4 retriever executed exactly 223 calls. Every configuration reused the same raw pools and
computed `rrf_score / (1 + weight * (1 - identity_token_coverage))`. Results:

| Weight | Eligible | Old R@5 | Old R@1 | New required | Forbidden cases |
|---:|---:|---:|---:|---:|---:|
| 0 | yes | 168/168 | 165/168 | 24/24 | 18/24 |
| 0.05 | yes | 168/168 | 165/168 | 24/24 | 18/24 |
| 0.1 | yes | 168/168 | 165/168 | 24/24 | 18/24 |
| 0.25 | yes | 168/168 | 165/168 | 24/24 | 18/24 |
| 0.5 | yes | 168/168 | 165/168 | 24/24 | 18/24 |
| 1 | yes | 168/168 | 165/168 | 24/24 | 18/24 |
| 2 | yes | 168/168 | 165/168 | 24/24 | 18/24 |

Only five of all 223 pools contain more than five candidates. The 24 safety pools have median size
three; nine have two candidates, eight have three, and only two exceed five. Reordering therefore
cannot remove most wrong neighbors from a Top-5 response. This explains why every setting has the
same aggregate result and why baseline is a fallback rather than a successful selection.

Selection JSON SHA-256 is
`15ef98ddf75df7e4d8fe0e1c7dcacd3c5a37e590943df507d7eb3c6eebbf6334`. The private 20-case
evaluation was not opened or rerun. API, runtime retriever, PostgreSQL, canonical catalog, and Dual
RAG behavior remain unchanged. Thirteen focused and all 739 repository tests pass.
