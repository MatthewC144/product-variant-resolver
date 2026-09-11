# Family-Level Human Knowledge — Requirements

> Mode: Lite / Lean Industrial
>
> Phase: Specification
>
> Status: Confirmed by project owner on 2026-09-11; implementation in progress
>
> Source registry: `fandom-2025-review-families-r790665-v1`

## Purpose

Add the 42 accepted review-family identities to the existing non-canonical human-knowledge RAG
source without pretending they are variants, indexing any of the 7 held families, duplicating the 4
accepted merges, or allowing review knowledge to influence canonical identity decisions.

## Functional requirements

### FHK-R1 — Deterministic runtime projection

WHEN the projection builder receives the frozen review-family registry and manifest, THE SYSTEM
SHALL verify their filenames, schemas, versions, checksums, 42/4/7 accounting, and 100 held release
references before producing a separate family-knowledge projection.

### FHK-R2 — Exact projection scope

WHEN projection succeeds, THE SYSTEM SHALL emit exactly 42 `review_family` documents from
`new_families`, SHALL NOT emit a new document for any merge link, and SHALL NOT emit any hold
exclusion or held release as a searchable document.

### FHK-R3 — Conservative searchable text

WHEN a review-family document is indexed, THE SYSTEM SHALL derive searchable text only from its
brand, approved display name, and approved aliases; decision reasons, evidence URLs, source-record
IDs, toy/collector numbers, series, variant notes, and held names SHALL remain non-searchable.

### FHK-R4 — Frozen projection manifest

WHEN projection output is generated, THE SYSTEM SHALL create a manifest that freezes the registry
and registry-manifest checksums, projection checksum, fixed 42-document count, 4 skipped merge
links, 7 skipped holds, 0 variant documents, and 0 canonical/PostgreSQL promotions.

### FHK-R5 — Discriminated knowledge documents

WHEN the human-knowledge catalog loads, THE SYSTEM SHALL preserve existing provisional-variant
documents and add review-family documents as a distinct `knowledge_type`; it SHALL require globally
unique knowledge UUIDs/IDs and identity statuses appropriate to each type.

### FHK-R6 — Unified hybrid retrieval

WHEN a title is resolved, THE SYSTEM SHALL search one combined 142-document human-knowledge pool
using the existing deterministic sparse, hashing-dense, and RRF process, rank both document types in
one bounded result list, and use a common knowledge UUID only for scoring/tie-breaking.

### FHK-R7 — Family self-retrieval smoke gate

WHEN each of the 42 approved family display names is queried with its brand, THE SYSTEM SHALL return
the corresponding review-family document within the first 5 human-knowledge results; this is a
wiring smoke gate, not a generalization or production-accuracy claim.

### FHK-R8 — Existing variant regression

WHEN an existing reviewed human-label query is resolved, THE SYSTEM SHALL continue to return its
expected provisional-variant candidate with unchanged identity fields and SHALL distinguish it with
`knowledge_type=provisional_variant`.

### FHK-R9 — Hold and merge behavior

WHEN a held family name is queried, THE SYSTEM SHALL return no `review_family` document for that
family; WHEN an accepted merge family is queried, THE SYSTEM SHALL rely on its existing provisional-
variant documents and SHALL NOT return a duplicate review-family identity.

### FHK-R10 — Canonical isolation

WHEN any human-knowledge candidate is retrieved, THE SYSTEM SHALL keep it outside canonical
candidate fusion, reranking, calibration, decision policy, confidence, and final product selection;
review-family IDs/UUIDs SHALL never populate response canonical fields.

### FHK-R11 — Debug-only API contract

WHEN debug output is requested, THE SYSTEM SHALL return one bounded
`human_knowledge_candidates` list discriminated as `provisional_variant` or `review_family`, expose
only type-appropriate review IDs/metadata, and include the family-projection version; WHEN debug is
false, THE SYSTEM SHALL omit all human-knowledge candidates and versions.

### FHK-R12 — Safe debug UI

WHEN the debug UI renders a human-knowledge candidate, THE SYSTEM SHALL label its type, show family-
only status without a fabricated variant, preserve existing variant rendering, and insert all
external text through text-safe DOM operations.

### FHK-R13 — Readiness and fail-closed behavior

IF the projection or manifest is missing, stale, malformed, checksum-invalid, includes a hold/merge,
contains duplicate/unsupported identity, or widens its usage boundary, THEN THE SYSTEM SHALL report
the family-knowledge dependency not ready and SHALL return HTTP 503 without canonical identity.

### FHK-R14 — Versioning and observability

WHEN the combined index is ready, THE SYSTEM SHALL identify it as `human-knowledge-hybrid-v2`,
publish the human catalog and family-projection versions in debug/health metadata, keep the existing
`human_knowledge_retrieval` timing, and record bounded total/type candidate counts without logging
raw titles.

### FHK-R15 — Persistence and evaluation boundary

WHILE this feature is in Lite runtime-integration scope, THE SYSTEM SHALL NOT change PostgreSQL
schema/data, canonical catalog data, calibration/threshold artifacts, or production-quality claims;
the family source SHALL remain debug-only pending an independent casting-grouped holdout evaluation.

### FHK-R16 — Reproducibility and regression gate

WHEN the feature is verified, THE SYSTEM SHALL reproduce the projection byte for byte, pass focused
loader/retrieval/API/UI/readiness tests, pass the complete existing suite and deterministic data
chain, and preserve the frozen canonical evaluation metrics.

## Acceptance boundary

Passing this feature proves that accepted family names can be retrieved and explained as a second-
RAG review suggestion without changing canonical answers. It does not prove fuzzy/generalized
family retrieval quality, release-variant correctness, marketplace coverage, PostgreSQL scale, or
production readiness.

## Out of scope

- Resolving or indexing the 7 held families.
- Turning the 4 merge links into duplicate knowledge documents.
- Creating release variants from the 100 held source rows.
- Letting review-family candidates influence final identity or confidence.
- PostgreSQL ingestion or pgvector benchmarking for the family source.
- Importing additional yearly lists toward the approximately 3,000-row target.
