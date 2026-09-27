# Representative Hard Benchmark v1 data contract

This directory is the versioned, provenance-controlled home of the representative benchmark. At
RHB-T2 it contains **contracts and the read-only T1 source baseline only**. It is not yet an approved
benchmark dataset: the owner source decision (T3), canonical authority audit (T4), query authoring,
and labeling have not happened.

## Authority boundary

The validator in `src/product_variant_resolver/representative_benchmark.py` treats every artifact as
untrusted input and rejects unknown fields. In particular:

- a source may enter a case only for an explicitly allowlisted use after an `approved` owner
  decision, rights review, privacy review, and publication decision;
- `matched` requires an existing frozen-catalog UUID and an `approved_exact` authority record whose
  catalog-record checksum is current and whose verified fields cover every non-empty
  variant-defining catalog field;
- Human Knowledge, review-family IDs, owner staging rows, Wiki staging rows, family-only alignment,
  and a resolver candidate cannot create canonical truth;
- typed `authority_eligibility` and `authority_evidence_level` make that source boundary executable:
  all current real sources are prohibited, fixtures are regression-only, and only a future explicit
  `authorized_export` with `exact_variant_authority_candidate` and
  `independent_exact_variant` classifications can proceed to T3/T4 review;
- `ambiguous` and `no_match` never carry an expected canonical UUID;
- `held` and `rejected` labels never enter scored results;
- public artifacts require public-row redistribution and privacy approval; local-only evidence may
  be represented only by an approved opaque reference/digest and safe aggregates;
- authority, query, and label row artifacts allow only `public` or `local_only`; `aggregate_only`
  belongs to a separate safe manifest/summary and cannot disguise raw rows;
- public row artifacts reject obvious email/phone contact data in query, reviewer, family, reason,
  and evidence-reference text while preserving ordinary URI references;
- Test raw recursively rejects expected-label, target, correctness, metric, quality-gate, and winner
  fields. Its only label-related field is the required negative telemetry `labels_loaded=false`.

## Contract layers

| Layer | Schema version | Primary validator |
|---|---|---|
| Source inventory | `pvr-representative-hard-benchmark-source-inventory-v1` | `validate_source_inventory` |
| T1 source manifest | `pvr-representative-hard-benchmark-source-inventory-manifest-v1` | `validate_source_inventory_manifest` |
| Canonical authority | `pvr-representative-hard-benchmark-canonical-authority-v1` | `validate_canonical_authority` |
| Output-blind query pack | `pvr-representative-hard-benchmark-query-pack-v1` | `validate_query_pack` |
| Owner labels | `pvr-representative-hard-benchmark-labels-v1` | `validate_labels` |
| Family-safe split | `pvr-representative-hard-benchmark-split-v1` | `validate_split` |
| Frozen artifact manifest | `pvr-representative-hard-benchmark-manifest-v1` | `validate_frozen_manifest` |
| Label-blind Test raw | `pvr-representative-hard-benchmark-test-raw-v1` | `validate_label_blind_raw` |
| Joined scored rows | `pvr-representative-hard-benchmark-scored-results-v1` | `validate_scored_results` |

All models reject unknown fields. The layered functions then enforce rules that require two or more
artifacts—for example, checking that a canonical UUID exists in the supplied catalog, that an exact
authority predates a label, or that every frozen Test query appears once in raw output.

## Determinism and manifests

JSON checksums use UTF-8, two-space indentation, sorted keys, `ensure_ascii=false`, and exactly one
trailing newline. `content_sha256` and `stable_json_bytes` are the shared implementation. A complete
manifest binds:

- the exact artifact checksum;
- the exact ordered case IDs and record count;
- the complete, sorted parent path/checksum set;
- declared counts, publication scope, creator/time, and config/model/index versions;
- `status=complete`—partial/interrupted artifacts are invalid and must not replace a frozen output.

Changing content, order, parent inputs, catalog records, or a declared version creates a new
artifact/version. It must never overwrite v1 while retaining an old checksum.

## Current checked-in files

- `source-inventory.json`: six T1 sources with current and prospective use boundaries.
- `source-inventory-manifest.json`: checksums, aggregate counts, and repository tracking contract.

These files show that the source Gate is still pending and that current real data has zero exact
canonical mappings. No T3 approval is implied by this README or by successful schema validation.

## Local verification

```bash
.venv/bin/pytest tests/evaluation/test_representative_benchmark_contract.py -q
.venv/bin/ruff check src/product_variant_resolver/representative_benchmark.py \
  tests/evaluation/test_representative_benchmark_contract.py --select F,I
.venv/bin/mypy --strict src/product_variant_resolver/representative_benchmark.py
```

The contract module has no network, browser, FastAPI, resolver-service, or catalog-mutation
dependency. Later tasks may call these validators but must not weaken them to make a dataset pass.
