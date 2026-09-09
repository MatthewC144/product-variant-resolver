# Review-Family Materialization — Requirements

> Mode: Lite / Lean Industrial
>
> Phase: Specification
>
> Status: Confirmed and implemented by T46
>
> Input checkpoint: `fandom-2025-priority-two-batch-05-adjudicated-v1`

## Purpose

Convert the completed 53-family Wiki adjudication queue into a deterministic review-family
registry without inventing release variants, weakening the canonical identity boundary, or writing
to PostgreSQL. The registry will give the 42 accepted new-family outcomes stable review identities,
represent the 4 accepted merges as links to existing human-backed families, and preserve the 7
holds as explicit non-materialized exclusions.

## Functional requirements

### RFM-R1 — Frozen authoritative input

WHEN the registry builder starts, THE SYSTEM SHALL verify the final adjudicated queue, the frozen
100-row staging dataset, the existing human-backed catalog, and their manifests by filename,
declared version, and SHA-256 checksum; it SHALL additionally require `status=adjudicated` and zero
pending family decisions before producing output.

### RFM-R2 — Closed decision vocabulary

WHEN a family is read from the queue, THE SYSTEM SHALL accept only completed
`merge_existing_family`, `create_new_casting`, or `hold` decisions whose scope is
`casting_family_only` and whose variant decision is `hold`.

### RFM-R3 — Stable identities for accepted new families

WHEN a family has an accepted `create_new_casting` decision, THE SYSTEM SHALL emit exactly one
review-family entity whose public ID reuses the immutable `family_review_id` and whose UUID is
UUIDv5-derived from a fixed project namespace, source namespace, and that ID—not from its mutable
display name or registry version.

### RFM-R4 — Existing-family merge links

WHEN a family has an accepted `merge_existing_family` decision, THE SYSTEM SHALL emit one merge
link to the exact existing human-backed `casting_id` and `casting_uuid`, and SHALL NOT mint a second
family identity for the Wiki name.

### RFM-R5 — Explicit hold exclusion

WHEN a family decision is `hold`, THE SYSTEM SHALL retain its family ID, name, reason, evidence,
and source-row count in an exclusion section, and SHALL mark it ineligible for materialization or
retrieval indexing.

### RFM-R6 — No fabricated variants

WHEN source rows are attached to a review-family entity or merge link, THE SYSTEM SHALL preserve
them only as held release references and SHALL NOT create provisional variants, infer colors,
interpret series as identity, or treat toy/collector numbers as reviewed aliases.

### RFM-R7 — Conservative alias contract

WHEN aliases are generated, THE SYSTEM SHALL include only the owner-approved family display name
in the alias set and SHALL store its normalized form separately as the family key. A held name,
variant note, series label, toy number, collector number, or related-lineage name SHALL NOT become
an alias without a separate attributable decision.

### RFM-R8 — Complete provenance

WHEN an accepted family entity or merge link is emitted, THE SYSTEM SHALL retain the decision batch
ID, reviewer, decision time, written reason, evidence references, source record IDs, and source
revision/license references needed to trace it back to the frozen queue and staging dataset.

### RFM-R9 — Deterministic ordering and serialization

WHEN the same verified inputs are processed repeatedly, THE SYSTEM SHALL produce byte-identical
UTF-8 JSON and Markdown outputs using stable ordering, normalized formatting, and no build-time
timestamp.

### RFM-R10 — Manifest and accounting

WHEN output is generated, THE SYSTEM SHALL create a manifest containing input and output SHA-256
checksums plus counts for 42 new entities, 4 merge links, 7 exclusions, 79/9/12 source rows by
decision class, 100 held release references total, and zero variant or canonical promotion.

### RFM-R11 — Fail-closed validation

IF an input checksum, queue status, count, target family, UUID/ID uniqueness rule, decision scope,
variant hold, evidence reference, source-row assignment, or output checksum is invalid, THEN THE
SYSTEM SHALL exit non-zero without overwriting accepted output files.

### RFM-R12 — Runtime and persistence boundary

WHILE this feature remains at registry materialization scope, THE SYSTEM SHALL NOT modify the
canonical catalog, `human_backed_catalog.json`, API response contract, Dual-RAG runtime candidate
set, calibration/evaluation data, migrations, or PostgreSQL rows.

### RFM-R13 — Reproducible check mode

WHEN the builder is run with `--check`, THE SYSTEM SHALL build expected artifacts in memory, compare
them byte for byte with checked-in outputs, report the accepted/merged/held counts, and perform no
filesystem writes.

## Acceptance boundary

Passing this feature means the 42 accepted family concepts have stable review-layer identities and
the complete 53-family decision history has a deterministic registry representation. It does not
mean that any of the 100 Wiki releases is a reviewed variant, a canonical product, a PostgreSQL
record, or a runtime search result.

## Out of scope

- Resolving the 7 held family identities.
- Creating or approving release-level variants, colors, or canonical UUIDs.
- Updating the API or debug UI.
- Loading review-family entities into the second RAG source.
- PostgreSQL schema changes or ingestion.
- Importing additional yearly Wiki lists toward the approximately 3,000-row target.
