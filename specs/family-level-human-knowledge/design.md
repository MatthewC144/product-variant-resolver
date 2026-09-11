# Family-Level Human Knowledge — Design

> Mode: Lite / Lean Industrial
>
> Status: Ready for project-owner confirmation

## Overview

The current second RAG source contains 100 provisional-variant documents built from confirmed human
labels. Its model and API require a provisional variant ID, so directly inserting 42 family-only
entities would falsify their identity level. T46 also marks the adjudication registry itself as not
runtime-loadable.

This design keeps that audit registry immutable and derives a separately authorized 42-document
runtime projection. The human-knowledge retriever loads the existing 100 variant documents plus the
42 family documents into one deterministic 142-document pool. Canonical retrieval remains a
separate pipeline and the human pool remains debug-only.

## Architecture

```text
review_family_registry + manifest
                │
                ▼
 build_review_family_knowledge.py
                │
     42-family runtime projection + manifest
                │
                ├─────────────┐
                ▼             ▼
  existing 100 variant docs   42 review-family docs
                └──────┬──────┘
                       ▼
       HumanKnowledgeRetriever v2
        sparse + hashing dense + RRF
                       │
              debug candidates only
                       │
                       ✕ canonical ranking/policy/confidence
```

The T46 registry is never loaded directly by the service. Its current
`excluded_from=runtime_retrieval` contract stays true; the new projection is a different, checksum-
frozen artifact with explicit debug-retrieval eligibility.

## Interfaces

### Projection builder

```bash
python3 scripts/build_review_family_knowledge.py
python3 scripts/build_review_family_knowledge.py --check
```

Default inputs:

- `data/review_family_registry.json`
- `data/review_family_registry_manifest.json`

Default outputs:

- `data/review_family_knowledge.json`
- `data/review_family_knowledge_manifest.json`

The builder accepts explicit paths for tests, validates all input before atomic replacement, and
uses deterministic JSON without a build timestamp.

### Runtime configuration

`Settings` adds:

- `review_family_knowledge_path`, environment variable `PVR_REVIEW_FAMILY_KNOWLEDGE_PATH`.
- `review_family_knowledge_manifest_path`, environment variable
  `PVR_REVIEW_FAMILY_KNOWLEDGE_MANIFEST_PATH`.

Both default to the checked-in data files. Missing or invalid data makes the application not ready
instead of silently falling back to the 100-document v1 index.

### Debug API

`debug.human_knowledge_candidates` remains one bounded list but becomes a discriminated union.

Existing variant item:

```json
{
  "knowledge_type": "provisional_variant",
  "casting_uuid": "...",
  "casting_id": "...",
  "provisional_variant_uuid": "...",
  "provisional_variant_id": "...",
  "identity_status": "needs_canonical_review",
  "brand": "Hot Wheels",
  "casting": "BMW M3 GT2",
  "series_label": "Neon Speeders",
  "variant_label": "...",
  "human_label_names": ["..."],
  "example_initial_names": ["..."],
  "source_case_ids": ["..."],
  "sparse_rank": 1,
  "dense_rank": 1,
  "rrf_rank": 1,
  "matched_tokens": ["bmw", "m3", "gt2"]
}
```

New family item:

```json
{
  "knowledge_type": "review_family",
  "review_family_uuid": "...",
  "review_family_id": "fandom-family-...",
  "identity_status": "family_accepted_variants_unreviewed",
  "brand": "Hot Wheels",
  "casting": "Proton Saga",
  "aliases": ["Proton Saga"],
  "source_record_ids": ["fandom-row-..."],
  "sparse_rank": 1,
  "dense_rank": 1,
  "rrf_rank": 1,
  "matched_tokens": ["hot", "wheels", "proton", "saga"]
}
```

Both variants include sparse/dense/RRF scores. Type-inapplicable identity fields are absent rather
than null. `DebugPayload` adds `review_family_knowledge_version`; existing
`human_catalog_version` remains.

## Data models

### `ReviewFamilyKnowledgeProjection`

- `schema_version=pvr-review-family-knowledge-v1`.
- `knowledge_version=review-family-knowledge-fandom-2025-r790665-v1`.
- `status=debug_retrieval_only`.
- `eligible_for=[human_knowledge_debug_retrieval]`.
- `excluded_from` includes canonical response/ranking, calibration, thresholds, evaluation ground
  truth, variant identity, and PostgreSQL ingestion.
- `documents` contains exactly 42 entries copied from accepted new-family identities.

Each document contains `knowledge_type`, review family ID/UUID, identity level/status, brand,
casting, approved aliases, and source record IDs. The runtime searchable-text property uses only
brand/casting/aliases. Source IDs remain debug provenance and are not indexed.

### Internal discriminated union

- `HumanVariantKnowledgeDocument` retains the current casting/provisional-variant fields.
- `ReviewFamilyKnowledgeDocument` contains only family-appropriate fields.
- Both expose internal `knowledge_uuid`, `knowledge_id`, `knowledge_type`, and `searchable_text`
  properties used by the retriever; family IDs never populate variant or canonical properties.
- `HumanKnowledgeCatalog` stores source versions and the combined typed documents.

### Candidate schema

`HumanKnowledgeCandidate` continues to pair one typed document with sparse/dense/RRF ranks, scores,
and matched tokens. Pydantic uses `knowledge_type` as the discriminator so OpenAPI and the UI can
reliably select type-specific fields.

## Retrieval and decision flow

1. Application startup loads the canonical catalog and existing human-backed catalog.
2. It loads the family projection and verifies its manifest checksum/version/count/usage boundaries.
3. Loader rejects any family document not present in the approved 42-document projection contract,
   any duplicate global knowledge ID/UUID, and any variant/canonical field in a family document.
4. The retriever builds one token index and one 192-dimensional hashing vector per typed document.
5. Query eligibility still requires at least one shared normalized token.
6. Sparse and dense orders use the common knowledge UUID for deterministic tie-breaking; RRF uses
   the existing constant and returns at most the shared candidate limit.
7. Human candidates are converted only to the discriminated debug union.
8. Canonical candidates independently enter structured fusion, reranking, calibration, and policy.
   No edge exists from the human candidate list to canonical selection.

Because the combined pool changes document frequencies, the order of human debug suggestions may
change. This is accepted for T47 only with regression/smoke tests; independent retrieval quality is
deferred to T48.

## Health and observability

Health adds a `review_family_knowledge` dependency with projection version and the detail
`family-only review suggestions; never canonical identity`. The existing `human_knowledge_index`
reports `human-knowledge-hybrid-v2`.

The current `human_knowledge_retrieval` timing remains one end-to-end measurement. Its trace span
adds bounded `variant_candidate_count` and `family_candidate_count`; logging continues to record
only request ID, title length, status, and duration—not the raw title or external names.

## UI behavior

The existing reviewed-name table gains a Type column. Variant candidates keep their current human
name and series/variant display. Family candidates show approved aliases, brand/casting, and
`family only — variants unreviewed` in the variant column. All values continue through `safeText`;
no `innerHTML`, HTML interpolation, or remote resource load is introduced.

## Error handling

- Projection builder errors name the failed invariant and return non-zero without overwriting good
  outputs.
- Loader errors for missing/malformed/stale projection or manifest prevent service construction.
- Health returns 503 and identifies the dependency as unavailable; `/resolve` returns the existing
  generic dependency-unavailable envelope with null/absent canonical identity.
- Unsupported knowledge types/statuses, held or merge documents, duplicate IDs/UUIDs, unapproved
  searchable fields, non-42 counts, and usage-boundary widening all fail closed.
- Debug serialization never coerces one document type into another.

## Security notes

The service reads checked-in local JSON only and does not fetch evidence URLs. External names and
source IDs are treated as untrusted strings. The projection builder selects a fixed allowlist of
fields; evidence text, URLs, variant notes, and toy numbers are not copied into searchable text.
Pydantic strict/discriminated models prevent ambiguous payload shapes, and the UI uses text nodes.

## Testing strategy

- Projection tests: exact 42 output, 4/7 skips, checksums, deterministic `--check`, allowlisted
  fields, no holds/merges/releases, and invalid-input preservation.
- Loader tests: both typed document shapes, exact 142 total, global ID/UUID uniqueness, manifest
  validation, usage boundaries, and rejection of wrong type/status/fields/count/checksum.
- Retrieval tests: all 42 exact brand/name queries recover their family within Top-5; BMW remains an
  expected provisional-variant result; all seven holds yield no corresponding family document; four
  merges yield no duplicate family document.
- Service/API tests: exact family query exposes family debug data while final canonical identity is
  null; default response omits debug; bounds apply across both types; health/version and missing/
  corrupt projection behavior are correct.
- UI tests: both types render safely, including markup-shaped external names; no fabricated variant
  text or unsafe DOM API.
- Regression: full suite, deterministic data chain, fixture validator, canonical evaluation report,
  Python compilation, Compose configuration, and whitespace checks.

## Deferred work

T48 creates an independently authored, casting-grouped holdout set and measures family-source
retrieval quality. Only after that evidence may T49 design PostgreSQL persistence and pgvector scale
measurement. Additional yearly-list ingestion toward approximately 3,000 rows follows those gates.
