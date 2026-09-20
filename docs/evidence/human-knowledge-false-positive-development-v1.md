# Human Knowledge false-positive development v1 — evidence

Date: 2026-09-20. Lite / Lean Industrial. Status: **baseline recorded; no mitigation selected**.

The new development pack contains 24 manually specified related-identity pairs from the committed
142-document Human Knowledge corpus. Every query has one required document and one distinct
forbidden document, and the pair shares at least one normalized identity-core token. Queries add
context and do not equal either indexed identity. Pack SHA-256 is
`dfeacb5092ee2e8af0a1aee5a53c63427421014b5077b59694d0371b0680ff65`; its manifest SHA-256 is
`8ff171769998bb1376f3668bf439b45696694ac23092a338c29c502a33e9246b`.

Pack construction loads only `human_backed_catalog.json`, `review_family_knowledge.json`, its
manifest, and the builder source. It does not reference the private local projection/evaluation
paths, and its manifest records that retrieval had not yet executed. After the pack was frozen, the
selected Human Knowledge RAG v4 baseline ran once at Top 5 with character floor 0.5, character RRF
weight 1.0, and 192-dimensional `hashing-v1` vectors.

All 24 required documents ranked first, so required Recall@5 is `1.0`. Eighteen cases also returned
their specified forbidden document, producing a forbidden-case rate of `0.75` and safety accuracy
of `0.25`; retrieval errors are zero. The baseline therefore confirms that the current retriever is
excellent at broad candidate recall on these related identities but weak at excluding a known wrong
neighbor. Baseline JSON SHA-256 is
`617d4192ec22009ca46d16bf929adb18af1c90ca48079ced61ab19c11635414b`.

This is intentionally development evidence. It makes no final-accuracy, population, release,
color, canonical, or runtime claim. No mitigation threshold or winner exists yet, and the private
20-case local-family evaluation was neither loaded nor rerun. Twelve focused tests and all 711
repository tests pass; targeted static/type/compile checks and deterministic `--check` pass.
