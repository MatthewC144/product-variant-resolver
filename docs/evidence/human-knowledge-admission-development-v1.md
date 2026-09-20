# Human Knowledge admission-policy development v1 — evidence

Date: 2026-09-20. Lite / Lean Industrial. Verdict: **experiment valid; no mitigation qualified**.

Protocol SHA-256 `b94592fba077f4d8592455fda38ed1033163d76bbeb773834329613630ed018a`
froze five minimum identity-token coverage thresholds (`0`, `0.5`, `2/3`, `0.75`, `1.0`), token
matching semantics, exact development denominators, recall/governance gates, and deterministic winner
ordering before grid execution. The protocol uses the committed 142-document corpus, existing
199-case development pack, and new 24-case false-positive pack only. It contains no private local
projection or test-evaluation path.

The current v4 retriever executed exactly 223 calls at Top 5. All five policy configurations reused
those same raw candidates; only the frozen post-retrieval coverage admission changed. Results:

| Coverage | Eligible | Old positives | New required | Forbidden cases |
|---:|---:|---:|---:|---:|
| 0 | yes | 168/168 | 24/24 | 18/24 |
| 0.5 | no | 167/168 | 24/24 | 7/24 |
| 2/3 | no | 165/168 | 24/24 | 2/24 |
| 0.75 | no | 159/168 | 23/24 | 0/24 |
| 1.0 | no | 152/168 | 22/24 | 0/24 |

The frozen selection rule returns baseline because it is the only eligible configuration. This is a
fallback result, not a successful mitigation or permission to activate runtime. The experiment shows
that global hard coverage filtering has a real precision–recall tradeoff: stricter settings remove
wrong neighbors, but also remove typo, abbreviation, or otherwise valid candidates.

Selection JSON SHA-256 is
`f073562bf2798652e1ccdde1f23d067fecda10851e132964be1aca82c125d71d`. The private 20-case local
evaluation was not opened or rerun. API, `HumanKnowledgeIdentityRetriever`, PostgreSQL, canonical
catalog, and Dual RAG runtime remain unchanged. Fifteen focused and all 726 repository tests pass.
