# Canonical Catalog Application v1 — Lean Specification

Date: 2026-09-30. Mode: Lean Industrial. Status: **APPLIED AND INDEPENDENTLY VERIFIED**.

## 1. Product goal and authorization boundary

Atomically apply the 20 CAR-T4 catalog proposals whose owner decisions are already approved to
`data/catalog.json`. The authorization scope is exactly:

- apply all 20 reviewed proposals as catalog records;
- preserve `color=null` and `edition=null`;
- publish only the resulting catalog rows and safe aggregate/hash metadata;
- do **not** approve exact authority, build an authority bundle, rerun RHB-T4, or authorize RHB-T5.

The implementation must retain the owner's exact application response in a Git-ignored private
event. It must not invent, correct, paraphrase, or publish that response. Catalog inclusion means
only that an owner-approved canonical catalog identity exists; it is not manufacturer-certified or
`approved_exact` truth.

## 2. Scope

In scope:

- validate the frozen 120-record parent catalog, 20-proposal packet, complete 20-event decision
  ledger, and separate application authorization;
- materialize 20 deterministic non-synthetic catalog rows;
- create a recoverable atomic transaction for the catalog, data manifest, public application
  manifest, and private application event;
- preserve historical CAR and RHB parent lineage and provide idempotent `apply` / `--check` modes;
- verify runtime loading and existing benchmark behavior after the catalog grows to 140 records.

Out of scope:

- changing any frozen proposal, packet, decision event, source decision, or prior RHB artifact;
- inferring color, edition, aliases, rarity, physical attributes, or additional identifiers;
- exact-authority review, CAR-T5 bundle creation, RHB-T4 re-audit, RHB-T5, model training, threshold
  tuning, network access, source collection, or publication of private reviewer text.

## 3. Observable requirements

### CCA-R1 — Exact parent and authorization

WHEN application is requested, THE SYSTEM SHALL require the original catalog raw SHA-256
`0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261`, version `fixture-v1`,
120 products, frozen packet SHA-256
`8997392511b1eb7a55abab3573f9773a57cb3501df5ed01d124952fc6df70ddd`, proposal-bundle SHA-256
`cd7da71b0635d2fdec3531aa4b5cdbf84df925448e1ae4cdef1a765676779898`, and a valid complete
decision ledger with exactly 20 `approve_catalog_record` events, zero held/rejected/pending events,
and `next_pending_ordinal=null`.

WHEN the owner application authorization is supplied, THE SYSTEM SHALL bind its exact verbatim text,
reviewer role, confirmation method, aware timestamp, packet/proposal/ledger hashes, parent catalog
hash, and the scope “apply these 20 records only; exact authority and RHB-T5 remain unauthorized.”
The mutable private event SHALL NOT be allowed to authorize itself; the caller must provide the exact
response and scope independently during the write and precommit verification.

### CCA-R2 — Complete batch or no application

WHEN the batch is built, THE SYSTEM SHALL cover exactly the 20 packet entries in canonical packet
order and prove a one-to-one match among candidate ID, proposal ID, proposed UUID, proposal SHA,
product-record SHA, decision event, and output catalog row. IF any proposal is missing, duplicated,
reordered, held, rejected, unreviewed, stale, or bound to another packet/catalog, THEN no output
SHALL be promoted.

### CCA-R3 — Non-inventive materialization

WHEN a proposal becomes a raw catalog row, THE SYSTEM SHALL use this deterministic mapping:

| Catalog field | Materialization rule |
|---|---|
| `canonical_uuid` | Exact `proposed_canonical_uuid`. |
| `canonical_id` | Deterministic slug of `Hot Wheels`, approved casting, release year, and toy identifier. |
| `brand` | Structural catalog constant `Hot Wheels`. |
| `casting`, `release_year`, `series`, `collector_number`, `series_position` | Exact proposed values supported by the six approved mappings. |
| `color`, `edition` | `null`; never derived from variant notes. |
| `release_key` | Exact proposal `release_key`; persisted as the release discriminator. |
| `near_duplicate_group` | Exact proposal `family_group_key`. |
| `identifiers` | One typed `toy_number` record carrying the exact approved identifier and frozen source-row reference. |
| `aliases` | Empty list; no alias is inferred. |
| `rarity_tier` | `null`. |
| `provenance` | Frozen source row/page/revision/timestamp/checksum, CC-BY-SA attribution/share-alike, and a note that catalog inclusion is not exact authority. |

The variant note SHALL remain review context outside the catalog row. The materializer SHALL use no
current-time value in catalog bytes and SHALL perform zero resolver/model or network calls.

### CCA-R4 — Identity and collision safety

BEFORE writing, THE SYSTEM SHALL normalize and compare identities against all 120 parent records and
all 20 proposals. It SHALL reject every unapproved collision described below.

| Collision class | Required behavior |
|---|---|
| Canonical UUID | Reject any duplicate across parent or proposals. |
| Canonical ID | Reject any duplicate generated slug. |
| Release key | Reject any duplicate explicit `release_key`; parent rows without one retain legacy identity behavior. |
| Identifier | Reject duplicate normalized `(identifier_type, identifier_value)` pairs across all 140 rows. |
| Parent natural key | Reject a proposal colliding with a legacy parent natural key. |
| Proposal natural key | Permit repeated natural fields only when every row has a distinct explicit release key, toy identifier, UUID, and canonical ID. |
| Family/release binding | Reject a release key or proposal whose family key differs from the frozen candidate. |

The current 20 proposals intentionally form seven repeated natural-key groups because unknown
color/edition cannot distinguish their releases. The implementation SHALL represent those releases
with their approved toy identifiers and release keys; it SHALL NOT disable collision checking or
invent physical fields to force uniqueness.

### CCA-R5 — Catalog version and ordering

WHEN the identity set changes from 120 to 140 records, THE SYSTEM SHALL set
`catalog_version="catalog-v2"`. It SHALL retain `dataset_version="fixture-v1"` solely as the
unchanged benchmark/base-fixture lineage and SHALL record the distinction in `data/manifest.json`.
The source note SHALL state that the catalog contains 120 synthetic regression rows plus 20
owner-approved community-snapshot catalog rows and that catalog inclusion is not exact authority.

The original 120 records SHALL remain first, in their existing order, and byte-equivalent at the
canonical individual-record level. The 20 new records SHALL follow in canonical packet order. JSON
encoding SHALL be UTF-8, sorted keys, two-space indentation, and one trailing newline. The final
counts SHALL be exactly 140 total, 120 synthetic, and 20 non-synthetic.

### CCA-R6 — Atomic transaction and recovery

WHEN applying the batch, THE SYSTEM SHALL first derive and validate all final bytes without mutating
tracked state. It SHALL write exclusive same-filesystem temporary files, fsync files and containing
directories, and maintain a private transaction journal containing expected parent/child hashes and
rollback bytes. It SHALL then replace the catalog, data manifest, public application manifest, and
private event as one recoverable transaction and validate the complete post-state.

IF any validation, write, fsync, or replacement fails, THEN the system SHALL restore every original
byte and leave no artifact claiming success. IF a process interruption leaves a journal, THEN the
next `apply` or `--check` SHALL deterministically recognize a complete child state or restore the
exact parent before continuing. Symlinked files, path traversal, unexpected files, partial pairs,
and ambiguous recovery states SHALL fail closed.

WHEN exact expected outputs already exist, `apply` SHALL return `unchanged`. `--check` SHALL never
write; it SHALL reconstruct the expected child from frozen parents and compare every byte, count,
hash, ordering rule, and transaction artifact.

### CCA-R7 — Private event and public manifest

The Git-ignored private application event SHALL contain:

- schema/application version and status;
- exact owner response, `project_owner`, `owner_attestation`, aware timestamp, and bounded scope;
- packet, proposal-bundle, decision-ledger, cumulative-event, event-head, parent-catalog, and planned
  child-catalog hashes;
- ordered bindings for all 20 proposal/product/decision/output-row hashes;
- constraints `catalog_application_only`, `exact_authority_not_approved`,
  `rhb_t5_not_authorized`, `color_must_remain_null`, and `edition_must_remain_null`;
- an authorization checksum covering the exact response and every bounded scope field.

The tracked public application manifest SHALL contain no verbatim response, private reviewer
identity, candidate names, owner questions, or raw private ledger. It SHALL publish only the private
event/authorization hashes, parent and child versions/hashes, safe parent artifact hashes, ordered
aggregate record digests, counts, ordering/encoding policy, publication/license metadata, and these
explicit effects:

```text
catalog_record_applied_count = 20
catalog_product_count = 140
synthetic_product_count = 120
nonsynthetic_product_count = 20
exact_authority_count = 0
rhb_t5_authorized = false
resolver_output_consulted = false
network_requests = 0
```

The frozen proposal bundle and decision-progress artifacts SHALL remain unchanged even though their
phase-local fields say `catalog_record_applied=false`; the application manifest becomes the sole
authoritative post-review application state and SHALL link back to those frozen parents.

### CCA-R8 — Historical lineage compatibility

WHEN historical CAR/RHB/alignment artifacts reference the 120-row `fixture-v1` catalog, THE SYSTEM
SHALL validate them against the exact application parent, not silently reinterpret them against the
140-row child. The parent SHALL be reproducible from the unchanged ordered first 120 records plus the
frozen parent header and SHALL reproduce the original raw SHA-256 exactly.

Existing RHB artifacts SHALL NOT be overwritten or have their authority claims/counts changed.
Historical validators/tests may use the reconstructed parent lineage; current runtime/catalog
validators SHALL use `catalog-v2`. The fixture generator SHALL refuse to silently overwrite an
applied catalog and SHALL require the catalog-application path to rebuild or verify the child.

### CCA-R9 — Runtime and Gate isolation

WHEN `catalog-v2` loads, THE runtime SHALL expose 140 unique products and the new toy identifiers
without relaxing existing schema, provenance, or duplicate checks. Existing fixture benchmark labels
SHALL remain unchanged; any measured resolver regression is a failed application Gate, not a reason
to relabel the benchmark.

Catalog application SHALL NOT create `AuthorityReviewEvent`, `approved_exact`, authority-bundle, or
RHB artifacts. It SHALL NOT change exact-authority count from zero or authorize RHB-T5.

## 4. Interfaces and artifacts

Proposed CLI:

```text
apply-canonical-catalog-proposals \
  --root <repository> \
  --owner-response <exact external response> \
  --authorized-exact-owner-response <same exact response>

apply-canonical-catalog-proposals --root <repository> --check
```

Implementation artifacts:

- `src/product_variant_resolver/canonical_catalog_application.py`
- `scripts/apply_canonical_catalog_proposals.py`
- `tests/authority/test_canonical_catalog_application.py`
- `data/authority-review/canonical-authority-review-v1/catalog-application-manifest.json`
- ignored `data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-application-event.json`
- atomically updated `data/catalog.json` and `data/manifest.json`

Compatibility changes may touch catalog loading, fixture validation/generation guards, and tests that
currently treat the historical 120-row parent as the mutable current catalog. They must not rewrite
the historical evidence itself.

## 5. Implementation tasks

1. **Catalog-v2 contract** `[backend]` — add child catalog/application models, deterministic row
   materialization, release-key-aware loader behavior, and collision tests without changing real data.
2. **Transactional applier** `[backend]` — add exact external authorization, private/public artifacts,
   atomic journal/recovery, `apply`, and read-only `--check`, verified only on temporary fixtures.
3. **Lineage compatibility** `[backend/qa]` — make fixture/current validators and tests distinguish the
   immutable 120-row parent from `catalog-v2`; add generator overwrite protection.
4. **Authorized application** `[task_executor]` — supply the owner's exact response externally, apply
   the complete batch once, verify `unchanged` replay, and commit the atomic application state.
5. **Lean verification and documentation** `[qa/doc_curator]` — run requirement-mapped QA and record
   engineering PASS separately from `exact_authority_count=0`.

## 6. Test and QA acceptance

Required positive verification:

- parent, packet, proposals, all 20 decisions, private authorization, and every hash binding validate;
- first application reports `created`; identical replay reports `unchanged`; repeated `--check` is
  byte-identical and read-only;
- catalog has exactly 140 unique UUIDs/IDs, 120 synthetic and 20 non-synthetic rows;
- every original record hash/order is unchanged, and all 20 new rows match their proposals;
- runtime/service loads `catalog-v2`, toy identifiers are searchable, and existing fixture benchmark
  expectations and measured regression budget remain unchanged;
- public outputs contain required CC-BY-SA attribution/share-alike metadata and no owner verbatim,
  PII, credentials, resolver/model output, or private row-review material.

Required negative and failure-injection verification:

- stale/wrong parent, packet, proposal, product, ledger, event-head, source, or authorization hash;
- 19/20 decisions, held/rejected/pending decision, reordered/duplicate/extra proposal, wrong owner
  scope, paraphrased exact response, or mutable event self-authorization;
- UUID, canonical ID, identifier, release-key, parent-natural-key, and family/release collisions;
- non-null/inferred color or edition, inferred alias/rarity, missing provenance/license, or altered
  original record;
- unsafe path/symlink, partial artifact set, tampered manifest, interrupted replacement, rollback
  failure, stale journal, and concurrent application attempt;
- attempted catalog overwrite through the fixture generator;
- any application-side creation of exact authority or RHB-T5 state.

Lean G2/G3 acceptance requires focused application/catalog/CAR tests, full repository regression,
fixture and lineage validation, resolver benchmark regression, Ruff, Ruff format, strict MyPy,
compileall, JSON/hash/link checks, secret/PII/license scan, and `git diff --check`. Engineering PASS
must be reported independently from the still-zero exact-authority result.

## 7. Rollback and next Gate

Before commit, rollback uses the private transaction journal to restore the exact 120-row parent and
all companion bytes. After a successfully committed application, rollback is not an in-place delete:
it requires a new explicit owner-authorized, versioned compensating catalog event that preserves the
v2 application history.

After successful application, the state is:

- 20 catalog records applied;
- 140 catalog products total;
- 0 approved exact-authority records;
- RHB-T5 unauthorized.

The next permissible Gate is a **separate CAR-T5 exact-authority owner Gate**. No authority bundle,
fresh RHB-T4 audit, or RHB-T5 work may begin from this catalog application alone.
