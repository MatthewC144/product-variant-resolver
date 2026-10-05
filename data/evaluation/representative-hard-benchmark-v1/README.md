# Representative Hard Benchmark v1 data contract

This directory is the versioned, provenance-controlled home of the representative benchmark. The
T1 source baseline, T3 source-decision overlay and historical T4 blocked audit remain frozen beside
the later CAR-T6 versioned T4 PASS. It is not yet an approved benchmark dataset: the separately
authorized RHB-T5 session created a private 60-case output-blind authoring artifact, but its
provisional challenge coverage has declared shortfalls and labeling remains unauthorized.

## Authority boundary

The validator in `src/product_variant_resolver/representative_benchmark.py` treats every artifact as
untrusted input and rejects unknown fields. In particular:

- a source may enter a case only when the T3 overlay has an `approved` source/use cell with a
  sufficient publication scope; downstream authority/query/label validators consult this overlay
  instead of treating mutable inventory flags as permission, and the overlay argument is mandatory;
- the source-decision artifact rejects unknown fields, binds the exact T1 inventory checksum and
  IDs, requires every source × six uses exactly once, and prohibits a passed Gate from containing
  `held` cells;
- typed downstream permissions independently restrict each source to `query_pack`, `scored_labels`,
  `family_context`, `canonical_authority`, `regression_only`, or `none`; free-text conditions cannot
  grant access;
- public Wiki queries must use a `source_record_ref` from the checksum-bound checked-in 100-row
  revision; arbitrary references are rejected;
- label validation revalidates serialized query-pack and canonical-authority dependencies against
  the same inventory/owner decision overlay, so preconstructed or later-mutated models cannot bypass
  their own source, scope, author, reviewer, or authority gates;
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
| T3 source decisions | `pvr-representative-hard-benchmark-source-decisions-v1` | `validate_source_decisions` |
| Canonical authority | `pvr-representative-hard-benchmark-canonical-authority-v1` | `validate_canonical_authority` |
| Private output-blind source | `pvr-rhb-t5-output-blind-source-v1` | `validate_materialized_projection` |
| Public projection manifest | `pvr-rhb-t5-output-blind-source-manifest-v1` | `validate_materialized_projection` |
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
- `source-decisions.json`: 66 owner-confirmed source/use cells bound to the exact inventory checksum;
  23 are approved for narrow scopes, 43 are rejected, and none are held. The approved scopes are
  10 `local_only`, 3 `aggregate_only`, and 10 `public_rows`; all 43 rejected cells are `prohibited`.
- `canonical-authority.json` and `canonical-authority-manifest.json`: the immutable historical
  zero-record RHB-T4 audit and its honest `blocked_insufficient_exact_authority` result.
- `canonical-authority-reaudit-v1.json` and `canonical-authority-reaudit-manifest-v1.json`: the
  separately authorized CAR-T6 re-audit with 20 approved exact records, seven qualifying families,
  zero shortfalls and `passed_exact_authority_gate`.
- `query-authoring-source-manifest.json`: aggregate-only proof that a 91-row private query-only
  projection was reproduced from the frozen 101-row source. It contains no row-level query text.
- `query-pack-manifest.json`: aggregate-only proof of the private 60-case RHB-T5 artifact. It
  contains no query, source-row reference, owner text, label, split, resolver output or rank, and it
  publishes the unresolved provisional challenge shortfalls.

The pre-authoring repair now writes the 91-row projection only to the exact Git-ignored
`local-query-authoring-v1/` directory with `0700/0600` permissions. Each private row contains only an
opaque `source_record_ref` and `query`; public Git receives only its irreversible hash and safe
aggregate counts. `BenchmarkQuery` no longer contains `split`; RHB-T7 remains the sole owner of the
separate family-safe `SplitArtifact`. The pre-authoring readiness command now closes immediately
after detecting the private Owner Gate ledger; it cannot be reused to inspect or restart the phase.

RHB-T5 selected 60 unique query/source/evidence-event rows across 53 provisional family groups. The
private pack remains `representative_pilot=false`. Query-surface coverage reaches the minimum for
same-casting/different-release, alias, missing-metadata and distractor-quantity classes, but publishes
shortfalls of year `3`, color `3`, series `4`, identifier `2` and unknown-to-catalog `4`. The last
class is intentionally zero because output-blind query text cannot establish catalog-relative
absence. Therefore this is a provenance/authoring artifact, not an accepted representative pilot.

Initial RHB-T6 readiness revalidated that pack through the core query contract and stopped before an
Owner Gate. The query source permits only `ambiguous/no_match`, leaving a frozen-baseline
matched-label permission shortfall of `20`; the CAR authority's Wiki evidence source is also not
admitted as source-wide exact authority by frozen T1/T3. No label, held-label or labels manifest
exists.

`rhb-t6-governance-repair-proposal.json` is the non-authorizing repair proposal. It binds the exact
query pack, CAR authority bundle, source inventory/decisions and readiness hash. The proposed
admission is bundle-specific: Human queries remain non-authoritative, the whole Wiki source is not
promoted, and every future matched label would require an owner-reviewed exact authority reference.
The file contains no raw query, source-row reference, owner response or label and reports
`rhb_t6_authorized=false`.

`rhb-t6-governance-overlay-v1.json` is the owner-approved, versioned repair. It applies only to query
pack SHA `97f7…858a` and the 20 exact records in authority SHA `72c1…3117`; the sorted authority ID
allowlist is explicit. It does not rewrite T1/T3, expose the private approval/query rows, promote the
whole Wiki source, claim manufacturer truth, verify color/edition, or authorize RHB-T6 labels.
Post-overlay readiness reports effective matched capacity `20`, zero permission shortfall, and
`ready_for_separate_owner_authorization`. The separate label-authoring Owner Gate is still required,
and provisional challenge shortfalls remain subject to per-row owner verification or hold.

That separate Label Review v1 Gate is now recorded privately. The review builder creates
`local-query-authoring-v1/rhb-t6-label-review-v1/evidence-packets.json` and
`staged-label-proposals.json` with `0700/0600` permissions. These ignored files contain row-level
queries and catalog/authority evidence; they are not labels and every proposal has
`owner_decision_recorded=false` and `score_eligible=false`.

`rhb-t6-label-review-manifest-v1.json` is the aggregate-only public proof. It records 60 staged rows:
`0 matched`, `5 ambiguous`, `4 no_match`, and `51 held`. No query has the unique allowlisted toy
identifier plus casting evidence required even to suggest matched. This means the overlay provides
legal capacity for up to 20 matched labels, but the current query pack does not supply the evidence
overlap needed to use that capacity. The 20/20/20 acceptance target remains unmet and is not padded.

`rhb-t6-label-review-progress-v1.json` tracks owner review using aggregate-only event sourcing.
Batches 1–2 cover twenty private cases: one approved catalog-relative `no_match` decision, nineteen
holds, zero matched decisions and zero verified challenge tags. Forty staged cases remain. Exact row
decisions and owner text stay in `0600` Git-ignored event files; no partial label artifact is created.

T3 passes only for the declared scopes. Human-name queries and `ambiguous`/`no_match` labels remain
local-only; they can never produce a `matched` label. Workbook rows are local-only family context and
cannot enter query packs or scored labels. Git receives only schema/hash/count/aggregate/non-sensitive
summaries for those private sources. The checked-in 100-row Wiki derivative may provide public
query/context only for its exact revision with attribution and no new collection, and cannot provide
scored labels. Every live external source remains rejected, `network_collection_authorized=false`,
and all sources in that original RHB decision remain rejected for exact authority. The historical
T4 therefore correctly audited the zero-real-exact starting point and stopped. A later, separately
governed CAR source/review path produced the frozen CAR-T5F bundle; CAR-T6 then published a new
versioned RHB-T4 re-audit instead of rewriting that historical result. The new Gate passes, but its
authorization explicitly excludes RHB-T5, query-pack authoring and label authoring.

## Local verification

```bash
.venv/bin/pytest tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_benchmark_source_decisions.py \
  tests/evaluation/test_representative_benchmark_query_projection.py \
  tests/evaluation/test_representative_benchmark_query_readiness.py \
  tests/evaluation/test_representative_benchmark_query_authoring.py \
  tests/evaluation/test_representative_benchmark_governance_repair.py \
  tests/evaluation/test_representative_benchmark_governance_overlay.py \
  tests/evaluation/test_representative_benchmark_label_readiness.py -q
.venv/bin/python scripts/build_representative_hard_benchmark_query_projection.py --check
.venv/bin/python scripts/build_representative_hard_benchmark_query_pack.py --check
.venv/bin/python scripts/validate_representative_hard_benchmark_label_readiness.py
.venv/bin/python scripts/build_representative_hard_benchmark_governance_repair_proposal.py --check
.venv/bin/python scripts/build_representative_hard_benchmark_governance_overlay.py --check
.venv/bin/python scripts/build_representative_hard_benchmark_label_review.py --check
.venv/bin/python scripts/build_representative_hard_benchmark_review_progress.py --check
.venv/bin/ruff check src/product_variant_resolver/representative_benchmark.py \
  src/product_variant_resolver/representative_benchmark_query_projection.py \
  src/product_variant_resolver/representative_benchmark_query_readiness.py \
  src/product_variant_resolver/representative_benchmark_query_authoring.py \
  src/product_variant_resolver/representative_benchmark_label_readiness.py \
  tests/evaluation/test_representative_benchmark_contract.py \
  tests/evaluation/test_representative_benchmark_source_decisions.py \
  tests/evaluation/test_representative_benchmark_query_readiness.py \
  tests/evaluation/test_representative_benchmark_query_authoring.py \
  tests/evaluation/test_representative_benchmark_label_readiness.py
.venv/bin/mypy --strict src/product_variant_resolver/representative_benchmark.py \
  src/product_variant_resolver/representative_benchmark_query_projection.py \
  src/product_variant_resolver/representative_benchmark_query_readiness.py \
  src/product_variant_resolver/representative_benchmark_query_authoring.py \
  src/product_variant_resolver/representative_benchmark_label_readiness.py \
  src/product_variant_resolver/representative_benchmark_reaudit.py
```

The contract module has no network, browser, FastAPI, resolver-service, or catalog-mutation
dependency. Later tasks may call these validators but must not weaken them to make a dataset pass.
