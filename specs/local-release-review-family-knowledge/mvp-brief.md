# Local release review-family knowledge projection — MVP brief

Date: 2026-09-19. Mode: Lite / Lean Industrial. Status: **implemented and verified**.

## Purpose and boundary

Derive five private, typed review-family knowledge documents from the completed local materialization
registry. These documents define a future offline-evaluation candidate corpus; they are not loaded by
the API, Human Knowledge RAG, canonical resolver, PostgreSQL, or Dual RAG runtime in this feature.

The project already contains a separate 42-document 2025 Wiki review-family projection. The new
projection must preserve its own lineage and prove that IDs, UUIDs, and normalized brand/casting or
alias identities do not collide with that existing corpus.

## Requirements

- **LRFK-R1 — Validated input.** WHEN projection starts, THE SYSTEM SHALL deterministically validate
  the private local registry and its complete packet/ledger lineage before reading relationships.
- **LRFK-R2 — Typed document shape.** WHEN one confirmed relationship is projected, THE SYSTEM SHALL
  create exactly one `review_family` document containing only review ID/UUID, identity status,
  brand, casting, owner-confirmed aliases, and source record IDs.
- **LRFK-R3 — Search allowlist.** Searchable fields SHALL be exactly `brand`, `casting`, and `aliases`;
  toy number, year, series, variant note, candidate evidence, color, and source ID SHALL not enter
  searchable text.
- **LRFK-R4 — Review-only identity.** Every document SHALL use
  `identity_level=casting_family_only` and `identity_status=owner_confirmed_variants_unreviewed`;
  knowledge UUIDs SHALL be deterministic namespace UUIDs and SHALL NOT be canonical UUIDs.
- **LRFK-R5 — Existing-corpus guard.** WHEN compared with the frozen 42-document projection, THE
  SYSTEM SHALL reject duplicate review IDs, UUIDs, or normalized brand-plus-casting/alias identities.
- **LRFK-R6 — Source preservation.** WHEN source references are projected, THE SYSTEM SHALL copy only
  sorted unique source IDs for provenance and SHALL reject duplicate assignment across documents.
- **LRFK-R7 — Usage boundary.** The projection SHALL be eligible only for offline retrieval
  evaluation and SHALL explicitly exclude runtime retrieval, canonical ranking/response/confidence,
  calibration, evaluation ground truth, PostgreSQL, and variant identity.
- **LRFK-R8 — No runtime mutation.** API settings, existing Human Knowledge RAG files, resolver code,
  PostgreSQL, canonical catalog, evaluation labels, and Dual RAG runtime SHALL remain unchanged.
- **LRFK-R9 — Determinism.** Rebuilding the same inputs SHALL reproduce document order, UUIDs,
  projection checksum, public manifest, and report byte for byte.
- **LRFK-R10 — Safe publication.** First publication SHALL create a private/public pair; exact rerun
  SHALL return `unchanged`; partial/conflicting outputs SHALL fail without overwrite; a failed
  first-time second write SHALL roll back only the first directory created by that attempt.
- **LRFK-R11 — Private/public split.** Full documents SHALL remain gitignored. Public output SHALL
  contain only input/output hashes, schema/version, allowlists, zero collision count, aggregate
  counts, and zero downstream effects—never labels, aliases, IDs, source rows, or toy numbers.
- **LRFK-R12 — Current result.** The current projection SHALL contain five documents and 18 unique
  provenance references, prove zero collisions with the existing 42-document corpus, and report
  zero runtime-indexed documents, canonical promotions, colors, SQL writes, or evaluation labels.

## Design

`release_casting_review_knowledge.py` validates the local materialization chain and the existing
42-document knowledge file. Each local relationship ID becomes the review-family ID. A UUIDv5 under
the local-projection namespace provides the typed retriever key without creating canonical product
identity. The first deterministic alias is the display casting; all owner-confirmed observed labels
remain aliases. Only brand/casting/aliases will be eligible as future query text.

The private projection is stored under the ignored local data tree. A committed manifest/report
freezes hashes, counts, allowlists, eligibility boundaries, and the zero-collision result. The runtime
loader is intentionally unchanged; offline retrieval evaluation must be specified separately.

## Tasks

- [x] **LRFK-T1** Implement projection, UUID, allowlist, collision, and integrity validators. _(→R1–R9,R12)_
- [x] **LRFK-T2** Implement safe/idempotent private-public publication and CLI check mode. _(→R10–R11)_
- [x] **LRFK-T3** Add deterministic, collision, privacy, tamper, idempotency, and rollback tests. _(→R1–R12)_
- [x] **LRFK-T4** Generate real artifacts, run QA, and update evidence, decisions, README, roadmap, and project log. _(→R1–R12)_

## Acceptance

Five private review-family knowledge documents cover 18 unique source references and have no ID,
UUID, or normalized identity collision with the existing 42-document projection. Only
brand/casting/aliases are search-eligible. Rebuild/check is deterministic; invalid, stale, partial,
or conflicting state fails closed. No runtime source, API response, canonical truth, database, or
evaluation label changes.
