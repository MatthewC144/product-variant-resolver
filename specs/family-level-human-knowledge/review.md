# Family-Level Human Knowledge — Lite QA Review

> Date: 2026-09-11
>
> Mode: Lite / Lean Industrial
>
> Scope: FHK-R1–FHK-R16
>
> Verdict: **PASS for the specified debug-only integration boundary**

## Verdict summary

T47 passes its Lite acceptance boundary. The service deterministically derives 42 accepted
`review_family` documents, combines them with 100 existing `provisional_variant` documents in one
142-document Human Knowledge RAG v2 index, and exposes the mixed ranking only through a bounded,
type-discriminated debug contract. Family candidates never enter canonical ranking, calibration,
policy, confidence, or final identity.

This verdict does not approve family retrieval as production-quality matching. The 42/42 Top-5
result queries the same exact family names used to build the documents, so it is a wiring smoke gate
with worst rank 2, not an independent accuracy measurement. PostgreSQL persistence, canonical
promotion, release-variant creation, and the approximately 3,000-row expansion remain excluded.

## Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| FHK-R1 | `test_review_family_knowledge_projection.py` validates frozen input filenames, versions, checksums, 42/4/7 accounting, and 100 release references. | PASS |
| FHK-R2 | Projection scope test and manifest verify exactly 42 new-family documents, 4 skipped merges, 7 skipped holds, and no held release documents. | PASS |
| FHK-R3 | Document allowlist and searchable-text tests restrict family indexing to brand, casting, and approved aliases. | PASS |
| FHK-R4 | Manifest tests freeze both inputs, projection SHA-256 `8615cbb...b9d7`, counts, fields, and zero variant/canonical/PostgreSQL promotion. | PASS |
| FHK-R5 | Typed loader tests verify 100 variants plus 42 families, correct statuses, and 142 globally unique IDs/UUIDs; API tests verify two strict union branches. | PASS |
| FHK-R6 | Human-knowledge unit/integration tests run both types through one sparse, `hashing-v1` dense, and RRF pool with one bound and common knowledge UUID. | PASS |
| FHK-R7 | `test_all_42_family_names_retrieve_the_expected_document_within_top_five` passes 42/42; fresh inspection records worst rank 2. This is smoke-only. | PASS (wiring only) |
| FHK-R8 | BMW regression remains `provisional_variant` at rank 1 with its original type-appropriate fields. | PASS |
| FHK-R9 | Merge/hold exclusion tests prove 4 merges create no duplicates and 7 holds create no family documents. | PASS |
| FHK-R10 | Service/API tests keep Proton Saga canonical `no_match` with null identity while exposing a debug-only family candidate. Frozen canonical metrics are unchanged. | PASS |
| FHK-R11 | API tests verify one discriminated mixed list, shared limits, family version metadata, opposite-type field absence, and complete debug omission by default. | PASS |
| FHK-R12 | Node DOM harness labels both types, shows the family-only state, preserves variant rendering, and keeps markup-shaped names inert through `textContent`. | PASS |
| FHK-R13 | Builder/loader/API negative tests reject missing, stale, malformed, checksum-invalid, widened, duplicate, hold, merge, and unsupported data; readiness/resolve return 503. | PASS |
| FHK-R14 | Health/API/trace tests verify `human-knowledge-hybrid-v2`, both source versions, the existing timing, bounded type counts, and no raw-title logging. | PASS |
| FHK-R15 | Git diff from pre-T47 commit `785bb8d` changes no canonical catalog, benchmark, calibration/policy, migration, or PostgreSQL implementation file. AI-eval evidence denies quality/persistence claims. | PASS |
| FHK-R16 | Projection and full source chain reproduce; 184/184 tests, evaluation/report generation, compilation, JS syntax, both Compose configurations, and whitespace checks pass. | PASS |

## Measured evidence

Fresh runtime inspection produced 100 provisional variants, 42 review families, 142 combined
documents, 142 unique knowledge IDs, and 142 unique UUIDs. All 42 exact brand/family queries found
their expected family within Top-5; worst rank was 2. BMW M3 GT2 remained a variant at rank 1.
Proton Saga appeared as `review_family` debug evidence while its canonical response remained
`no_match` with null canonical ID.

The complete Python suite passed 184/184 in 1.423 seconds. The final generated evaluation report
retained the 21-case synthetic fixture results: Recall@25 `1.0`, Top-1 `1.0`, hard-negative accuracy
`1.0`, precision `1.0`, false-match rate `0.0`, and coverage `0.8333`. Its fresh direct-pipeline p95
was `2.3898 ms` and in-process HTTP/ASGI p95 was `2.675 ms`; both exclude Docker, TCP, database,
concurrency, and production traffic.

The deterministic chain passed fixture and 100-row pilot validation, review, base queue,
priority-one evidence/decision, all five research batches, all five cumulative priority-two
decision checkpoints, the 42/4/7 family registry, and the 42-document runtime projection. Python
compilation, JavaScript syntax, default/PostgreSQL-profile Compose configuration, and
`git diff --check` also passed.

## Findings and limitations

No blocking finding remains for T47's stated scope. One initial QA batch omitted `PYTHONPATH=src`
for the pilot validator and stopped with a local import error. This was a command-environment issue,
not a product failure; the complete chain was restarted with the correct path and passed.

The host verification environment emits the previously documented Starlette legacy-`httpx`
TestClient deprecation warning. It is non-failing and unrelated to T47. Ruff and MyPy are not
installed in the available host environment, so this review does not claim those checks; executable
tests, strict runtime schema validation, compilation, and whitespace checks are the available
evidence.

The principal remaining product risk is evaluation leakage for the family source: indexed names
are also the smoke queries. Shared tokens can surface unrelated accepted families, and neither
fuzzy/noisy generalization nor release-variant correctness is measured.

## Carry-forward

T48 must create an independently authored, casting-grouped family retrieval holdout before any
accuracy, production-readiness, canonical-promotion, or PostgreSQL rollout claim. T49 may evaluate
PostgreSQL/pgvector persistence and latency only after that quality gate. Further yearly-list
ingestion toward approximately 3,000 reviewable records remains later work.
