# Dual-source RAG human-knowledge runtime — v2 evaluation

## Evaluation verdict

**PASS for deterministic debug-only wiring and safety. NOT EVALUATED for independent family
retrieval accuracy or production readiness.**

Human Knowledge RAG v2 searches 142 typed documents: 100 provisional variants derived from the
confirmed human-label dataset and 42 review families derived from the frozen 2025 Fandom review
registry. Sparse token overlap and the deterministic 192-dimensional `hashing-v1` representation
are fused with RRF. This is separate from the canonical fixture RAG; human results can appear only
inside debug output.

## Dataset and leakage disclosure

The variant corpus contains 100 provisional variants across 97 casting entities, built from 101
confirmed human labels. The family corpus contains 42 accepted family-only identities representing
79 reviewed source rows; 4 merge families, 7 held families, and all 100 release variants are absent
as new family documents. The projection checksum is
`8615cbb99b453673599e1f9baf54f6900314d7ba64e53a31ea7891c71810b9d7`.

The family smoke matrix is intentionally leaky for quality measurement: each query is the indexed
brand plus exact approved family name. Its 42/42 Top-5 result and worst rank 2 prove that all accepted
documents were loaded and can be recovered, but do not measure normalization, fuzzy matching,
unseen marketplace noise, or generalization. No family Recall@K, Top-1, precision, or false-match
quality claim is made from that matrix.

## Rubric assessment

| Rubric area | Result | Evidence and boundary |
|---|---|---|
| Dataset disclosure | PASS | Versions, construction, 100/42/142 counts, 42/4/7 decision split, provenance, and exclusions are frozen in manifests and T47 evidence. |
| Leakage control | NOT EVALUATED for family quality | Exact indexed names are the smoke queries. T48 must provide independently authored queries and casting-grouped splits. |
| Family retrieval/ranking quality | NOT EVALUATED | 42/42 within Top-5, worst rank 2, is accepted only as a wiring check. |
| Existing variant regression | PASS | `Hot Wheels BMW M3 GT2 Neon Speeders` retains the expected `provisional_variant` at rank 1. |
| Canonical isolation | PASS | `Hot Wheels Proton Saga` returns family debug evidence but canonical `no_match` and null identity. Human candidates have no path into canonical scoring or policy. |
| API/UI safety | PASS | Strict OpenAPI discriminator, type-inapplicable field absence, one shared limit, default omission, and inert markup-shaped DOM tests pass. |
| Failure safety | PASS | Invalid/missing/stale/widened family inputs fail readiness and resolve with HTTP 503 without fabricating identity. |
| Canonical regression | PASS (synthetic fixture only) | The unchanged 21-case fixture retains Recall@25/Top-1/precision `1.0`, false-match `0.0`, and coverage `0.8333`. This does not score family retrieval. |
| Latency | LIMITED SMOKE ONLY | Fresh in-process report records pipeline p95 `2.3898 ms` and HTTP/ASGI p95 `2.675 ms`; Docker, database, network, concurrency, and production are excluded. |

## Release boundary

The v2 result is approved only for local, bounded, debug presentation. Family IDs remain excluded
from canonical response, ranking, calibration, threshold selection, evaluation ground truth,
variant identity, and PostgreSQL ingestion. No external neural embedding or cross-encoder was used;
`hashing-v1` is deterministic feature hashing, and `heuristic-v1` remains a disabled ablation.

The next quality gate is T48. It must freeze independently written noisy queries, keep related
castings in one split, define relevance judgments without copying indexed names as answers, and
report raw ranks/errors before T49 persistence or the approximately 3,000-row expansion proceeds.

## Reproducible evidence

- Complete host suite: 184/184 passed.
- Exact family wiring matrix: 42/42 within Top-5; worst rank 2.
- Typed document inventory: 100 variants + 42 families = 142; all IDs/UUIDs unique.
- Canonical fixture: 21 test cases, 12 matched cases, unchanged metrics stated above.
- Data chain: all validators/builders through `review_family_knowledge --check` passed.
- Detailed traceability: `specs/family-level-human-knowledge/review.md` and
  `docs/evidence/family-level-human-knowledge-t47.md`.
