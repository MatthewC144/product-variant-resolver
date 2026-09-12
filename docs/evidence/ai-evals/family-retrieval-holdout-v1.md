# Human Knowledge RAG v2 — family-retrieval holdout v1

## Evaluation verdict

**FAIL for the precommitted independent family-retrieval gate.** The result is still valid and is
preserved as engineering evidence. Eight of nine gates passed; lexical-variation Recall@5 was
`31/42 = 0.7381`, below the frozen `>=0.75` requirement by one successful case. No query, label,
retriever, threshold, catalog, or runtime policy was changed after observing the result.

This verdict supersedes the earlier “not evaluated” family-quality status in
`dual-rag-human-knowledge-v2.md`. It does not invalidate that milestone's debug wiring and safety
result; it adds the previously missing independent retrieval-quality measurement.

## Frozen evaluation identity

The test set is `family-retrieval-holdout-v1`, containing 105 project-owner-approved synthetic
cases: 84 positive cases over 42 casting families, four merge controls, seven hold controls, and
ten zero-overlap unrelated controls. All cases are test-only. The benchmark SHA-256 is
`440246fb6a3b38f56fc25c1ec939d53d6cfc4457fed738aad561899325808afd`, and its manifest fixes the
existing `human-knowledge-hybrid-v2` retriever, 192-dimensional deterministic `hashing-v1`
representation, RRF `k=60`, and candidate limit `K=5`.

The benchmark was authored and committed before scoring, and every case declares
`retriever_output_viewed=false`. During scoring, the evaluator retrieves and serializes candidates
before accessing that case's `expected` branch. The complete ordered candidate ranks and scores are
stored in `reports/family-retrieval-v1/evaluation.json`; aggregate values are recalculated from that
raw array during validation and Markdown rendering.

## Precommitted gate results

| Criterion | Raw result | Gate | Verdict |
|---|---:|---:|:---:|
| Positive Recall@5 | `73/84 = 0.8690` | `>=0.85` | PASS |
| Positive Recall@1 | `58/84 = 0.6905` | `>=0.65` | PASS |
| Positive MRR@5 | `65.0/84 = 0.7738` | `>=0.75` | PASS |
| Lexical-variation Recall@5 | `31/42 = 0.7381` | `>=0.75` | **FAIL** |
| Marketplace-noise Recall@5 | `42/42 = 1.0000` | `>=0.75` | PASS |
| Family coverage@5 | `42/42 = 1.0000` | `>=0.90` | PASS |
| Merge-control Recall@5 | `4/4 = 1.0000` | `=1.0` | PASS |
| Forbidden family hits | `0` | `=0` | PASS |
| Unrelated non-empty results | `0/10` | `=0` | PASS |

The 84 positive results contain 11 misses: ten cases returned candidates without the expected
family and one returned no candidates. All 11 are lexical-variation cases. The perfect family
coverage is not contradictory: every family was recovered by at least one of its two challenges,
while 11 families failed their harder spelling, abbreviation, punctuation, or spacing variant.

## Rubric assessment

| Rubric area | Result | Evidence and boundary |
|---|---|---|
| Dataset disclosure | PASS | Versions, checksums, construction method, 105/84/42/4/7/10 counts, test-only split, and synthetic limitation are recorded. |
| Leakage control | PASS for the frozen v1 process | Query pack and owner labels were frozen before first retrieval; label-access-order and checksum-failure tests pass. The set is development-known after this result. |
| Family retrieval quality | **FAIL** | The independently authored lexical style misses its precommitted gate by one case. Overall Recall@5 passes but cannot override a style failure. |
| Merge and hold safety | PASS | All four merge controls recover an existing provisional casting, and no forbidden duplicate/held family is returned. |
| Unrelated-query safety | PASS | All ten zero-overlap controls return no candidates. |
| Traceability | PASS | Per-case candidates, types, ranks, scores, expected rank, and error categories reproduce all aggregates. |
| Canonical isolation | PASS by design boundary | The evaluator reads the debug human index only and does not write canonical catalog, policy, calibration, PostgreSQL, or benchmark files. Full regression is deferred to T48.5. |
| Production readiness | NOT EVALUATED | The challenge is synthetic, family-level, small-domain, local, and does not measure PostgreSQL/pgvector, concurrency, or production latency. |

## Failure interpretation and decision

The failure is concentrated rather than random: marketplace wrappers are handled, but token-level
misspellings and aggressive abbreviations can remove or dilute the exact shared tokens required by
the current eligibility step. Because `hashing-v1` dense scoring runs only after this shared-token
filter, it cannot rescue a query with no usable overlap, and broad human variant documents can
occupy the five available ranks when only generic tokens overlap.

This explanation is diagnostic, not a tuning instruction applied to v1. The repository keeps the
retriever unchanged and keeps the family source debug-only. T49 persistence/3,000-row scale work is
not authorized by this quality result. A later redesign may consider fuzzy candidate generation,
character-level eligibility, field-aware ranking, or a neural representation, but model selection
must use separate development evidence and final claims require a newly authored
`family-retrieval-holdout-v2`.

## Reproducibility and limitations

The evaluator and Markdown generator expose `--check`; their focused suite verifies formula
derivation, explicit error categories, retrieval-before-label access, invalid-input no-overwrite,
and byte reproducibility. The formal JSON links its exact query preprocessor checksum because token
cleanup is part of the executed query path even though the earlier system-under-test manifest
froze the normalizer and retriever source separately.

These results do not measure real marketplace traffic, release-level variant resolution, canonical
accuracy, confidence calibration, database scale, or production latency. With only 42 families,
small count changes visibly move percentages. After publication the v1 cases are no longer an
unseen final holdout, so rerunning the unchanged implementation is allowed only as a reproducibility
check—not as evidence for tuning a modified retriever.
