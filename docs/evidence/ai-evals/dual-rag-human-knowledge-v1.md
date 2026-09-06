# Dual-source RAG human-knowledge runtime — v1

## Implemented boundary

The resolver now executes two independent retrieval paths after one shared signal-extraction step.
The canonical path searches the 120-product fixture catalog through sparse, hashing-dense, and
structured retrieval, then uses RRF, optional reranking, calibration, and policy for the final
decision. The human-knowledge path searches 100 provisional variants through IDF-weighted sparse
overlap and the existing deterministic hashing embedding, then fuses both ranks with RRF.

Only the canonical path can populate `canonical_uuid`, `canonical_id`, and `product`. Human results
carry `needs_canonical_review`, human-reviewed names, source case IDs, matched tokens, and their own
ranks/scores. Both candidate lists are bounded by `debug_candidate_limit` and omitted when debug is
false.

## Focused observations

`Hot Wheels BMW M3 GT2 Neon Speeders` ranks the reviewed `BMW M3 GT2 / Neon Speeders` provisional
variant first with all distinctive tokens matched. Because the fixture catalog has no canonical BMW
M3 GT2, the final response remains `no_match` with null UUID and slug. A synthetic canonical query,
`2022 Chevy Nomad Red #101`, still returns its existing fixture UUID while the human path shows only
review evidence. A query with no shared tokens returns no human suggestion.

These are functional smoke observations, not a held-out retrieval-accuracy claim. The human catalog
contains the same reviewed aliases used to construct its documents, so self-retrieval would be a
tautological benchmark. A future evaluation must freeze distinct query examples or a grouped
holdout before reporting Recall@K or Top-1 for this second source.

## Verification

Unit tests cover strict catalog loading, top-ranked distinctive-token retrieval, empty retrieval,
and candidate limits. Integration/API tests prove the second source executes, remains non-canonical,
is debug-bounded and default-hidden, appears in timing/tracing and health metadata, and fails
readiness when its catalog is missing. The UI smoke harness verifies human-provided markup is
rendered through `textContent` rather than interpreted as HTML.
