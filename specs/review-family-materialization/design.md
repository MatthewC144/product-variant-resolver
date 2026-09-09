# Review-Family Materialization — Design

> Mode: Lite / Lean Industrial
>
> Status: Ready for project-owner confirmation

## Overview

The final adjudication queue contains human decisions at casting-family scope, while the existing
`human_backed_catalog.json` contains family entities only when at least one human-confirmed
provisional variant exists. Writing the 42 Wiki families directly into that catalog would require
fabricating a variant. This design therefore introduces a separate, review-only family registry.

The registry is a deterministic bridge between adjudication and future retrieval integration. It
does not change runtime behavior in this feature.

## Architecture

```text
final adjudicated queue + manifest          existing human-backed catalog
                 │                                      │
                 └──────── verified inputs ─────────────┘
                                    │
                    build_review_family_registry.py
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
      42 new entities         4 merge links        7 hold exclusions
             └──────────────────────┼──────────────────────┘
                                    │
              registry.json + report.md + manifest.json
                                    │
                         no runtime/database write
```

## Interfaces

### Builder CLI

```bash
python3 scripts/build_review_family_registry.py
python3 scripts/build_review_family_registry.py --check
```

Default inputs:

- `data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-05-adjudicated-queue.json`
- `data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-05-adjudicated-queue-manifest.json`
- `data/external/hot-wheels-wiki/pilot-2025/normalized.json`
- `data/external/hot-wheels-wiki/pilot-2025/manifest.json`
- `data/human_backed_catalog.json`
- `data/human_backed_catalog_manifest.json`

Default outputs remain inside the project:

- `data/review_family_registry.json`
- `data/review_family_registry_manifest.json`
- `reports/review-family-materialization.md`

The CLI accepts explicit input/output paths for tests. It validates all inputs before writing and
uses atomic replacement for the three outputs only after the complete build succeeds.

## Data models

### Registry envelope

```json
{
  "schema_version": "pvr-review-family-registry-v1",
  "registry_version": "fandom-2025-review-families-r790665-v1",
  "status": "review_family_only",
  "eligible_for": ["family_review", "future_human_knowledge_index"],
  "excluded_from": [
    "runtime_retrieval",
    "canonical_variant_response",
    "canonical_resolution_accuracy",
    "calibration_training",
    "threshold_selection",
    "postgresql_ingestion"
  ],
  "new_families": [],
  "merge_links": [],
  "hold_exclusions": []
}
```

### `ReviewFamilyEntity`

- `review_family_id`: the source `family_review_id` without rewriting.
- `review_family_uuid`: UUIDv5 of
  `product-variant-resolver:review-family:fandom-hot-wheels-wiki:<family_review_id>`.
- `identity_level`: fixed `casting_family_only`.
- `identity_status`: fixed `family_accepted_variants_unreviewed`.
- `brand`, `display_name`, and `normalized_family_key` from the accepted queue record.
- `aliases`: one accepted display alias in v1; normalized form is stored separately.
- `decision`: batch ID, reviewer, time, reason, and evidence references.
- `held_release_references`: source IDs, rows, years, toy/collector numbers, series, and variant notes,
  each with `review_status=held_for_variant_review`.

Release references are provenance, not nested provisional variants and not searchable aliases.

### `ReviewFamilyMergeLink`

- Source family review ID, display/normalized name, decision provenance, and held release references.
- `target_casting_id` and `target_casting_uuid` resolved from the frozen human-backed catalog.
- `identity_status=family_merge_accepted_variants_unreviewed`.
- No new review-family UUID is generated.

### `ReviewFamilyHoldExclusion`

- Family review ID, display/normalized name, decision provenance, evidence, and source-row count.
- `identity_status=held_not_materialized` and `retrieval_eligible=false`.
- Source row IDs may be retained for audit, but their values do not become aliases.

### Manifest

The manifest freezes every input and output filename/checksum, declared versions, namespace string,
and the full accounting split. It also declares `provisional_variant_count=0`,
`canonical_promotion_count=0`, `runtime_indexed_family_count=0`, and
`postgresql_row_count=0`.

## Identity and alias decisions

The source `family_review_id` is the stable public review identifier because it is already
checksum-bound across the queue and all decision batches. UUIDv5 supplies a standard database-safe
identifier without randomness. Display-name corrections can therefore occur later without changing
the identity.

The readable slug is not used as an identity key. Current analysis finds no exact-name or readable-
slug collision among the 42 accepted creations and the 97 existing human families, but relying on
that observation would make future yearly imports unsafe. The immutable source-family ID avoids
that failure mode.

Power Wheels Dune Racer does not become an alias of Bogzilla in v1. Its hold documents a likely
renamed lineage, but no owner-authorized merge exists. The same rule prevents ambiguous BNR32,
Standard Kart, Mazda, Nissan LBWK, Batman, and '55 Chevy names from entering search.

## Build algorithm

1. Read all inputs and verify their manifests, checksums, and declared versions.
2. Validate the queue as fully adjudicated and reconcile its summary with all 53 family records and
   exactly 100 source-row references.
3. Index the staging dataset by source record ID and reconcile each queue reference, source revision,
   and license; index the existing human catalog by normalized key, casting ID, and UUID.
4. Partition decisions into create, merge, and hold without changing queue order.
5. Reject an accepted creation that exactly collides with an existing human family; otherwise build
   new entities with source-ID-based UUIDv5 identities and conservative aliases.
6. Resolve merge targets against the frozen human catalog; reject missing, duplicate, or mismatched
   targets.
7. Build explicit hold exclusions; do not emit identity objects for them.
8. Check global ID/UUID/source-row uniqueness and the 42/4/7 plus 79/9/12 accounting split.
9. Serialize deterministically, derive checksums, and render a readable report.
10. In write mode, atomically replace outputs only after every validation succeeds; in check mode,
    compare expected bytes without writing.

## Error handling

- User/data contract errors raise a concise `ValueError` naming the failed invariant.
- The CLI catches expected validation errors, prints one non-sensitive message to stderr, and exits
  non-zero.
- Missing or malformed input never results in a partial registry.
- Existing checked-in outputs remain untouched when a build fails.
- `--check` reports stale or missing files independently and exits non-zero.

## Security notes

All external source text is untrusted data. The builder reads local frozen JSON only, does not fetch
URLs, execute source content, render raw HTML, or follow file paths from the data. Output paths come
only from CLI arguments. Evidence URLs and names are serialized as strings; future UI rendering must
continue using text-safe DOM operations.

## Testing strategy

- Unit-test UUID/ID stability, conservative aliases, partition logic, and target resolution.
- Assert the exact 42 new / 4 merge / 7 hold and 79/9/12 row split for the frozen pilot.
- Assert all 100 source records occur exactly once and every release reference remains held.
- Assert changed checksums, partial queues, pending/unsupported decisions, widened variant scope,
  missing merge targets, duplicate IDs/rows, and held-name leakage fail closed.
- Assert no output contains `provisional_variants` or a canonical UUID.
- Assert repeated builds and `--check` are byte-identical and non-mutating.
- Run the complete host suite plus fixture/pilot/data-chain, compilation, Compose, and whitespace
  checks before marking implementation complete.

## Deferred integration

A later specification will extend the human-knowledge loader with a distinct family-level document
type and explicitly decide whether/to what extent family names enter Dual-RAG debug retrieval. A
separate PostgreSQL design will follow after local behavior and held-out retrieval quality are
validated. Neither integration is implicit in this registry contract.
