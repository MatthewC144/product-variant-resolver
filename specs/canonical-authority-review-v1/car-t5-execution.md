# CAR-T5 exact-authority execution addendum

Status: **CAR-T5P and Owner Gate T5-G1 complete; T5-G2 Batch 1 recorded (3 approved exact /
17 reviewed / 0 staged), while CAR-T5F remains blocked on the other six batches**

Mode: Lean Industrial

Parent requirements: CAR-R3–CAR-R10

## 1. Goal and authorization boundary

Prepare, review and freeze an output-blind exact-authority bundle for the 20 catalog-v2 records
created by CAR-T4A. This addendum does not alter the authority claim: any accepted value is exact
only relative to the approved, frozen community snapshot.

The first separately scoped T5-G2 owner decision now authorizes only the three Mazda Autozam
entries in Batch 1 to move from `reviewed` to `approved_exact`, relative to the frozen community
snapshot. It does not authorize any other batch, an authority bundle, RHB-T4 re-audit or RHB-T5.
Catalog-application and T5-G1 authorizations cannot be reused as exact-authority authorization.

Current immutable anchors are:

- catalog version `catalog-v2`, SHA-256
  `e763c8739a76ab4cc9b66169aecd4aea241ee810d8a27cdfb7d05bcacd98562e`;
- 140 catalog records: 120 preserved synthetic fixtures and 20 applied non-synthetic records;
- catalog-application manifest status
  `catalog_namespace_batch_applied_exact_authority_pending`, raw SHA-256
  `cf1c95ec8985f80f9ee48c2d8af8b297f5e7d771eff3bb07990034643e4b37b4`;
- CAR-T4 packet SHA-256
  `8997392511b1eb7a55abab3573f9773a57cb3501df5ed01d124952fc6df70ddd`;
- catalog decision-ledger SHA-256
  `c1fe895d5fa525b49c9115ffc4883e0b6d54bc172a3af7dc2fcb73ab9bc39b85`;
- catalog proposal-bundle SHA-256
  `cd7da71b0635d2fdec3531aa4b5cdbf84df925448e1ae4cdef1a765676779898`.

The frozen CAR-T4 packet, proposal bundle and decision ledger remain historical, phase-local
artifacts. Their `catalog_review_required`, null UUID, `catalog_record_applied=false` and
`authority_approved=false` values must not be rewritten.

## 2. Scope and non-scope

In scope:

- reconcile the 20 frozen CAR-T4 candidates to the exact 20 applied catalog-v2 rows;
- generate a deterministic, local-only, output-blind owner packet;
- publish a safe preparation manifest containing only hashes, counts, status and attribution;
- after separate owner decisions, record append-only `reviewed` and final outcome events;
- freeze the authority bundle only after all event and composition checks pass.

Out of scope:

- changing `data/catalog.json`, the CAR-T4 packet/proposals/ledger, source decisions or candidate
  selection;
- inferring color or edition, or treating `variant_note` as a value for either field;
- consulting resolver/model output, collecting new evidence or making network requests;
- treating catalog inclusion as exact authority;
- RHB-T4 re-audit, RHB-T5, benchmark labels, model work or threshold changes.

## 3. Observable requirements

### T5E-R1 — Preparation cannot decide

WHEN CAR-T5 preparation runs without a qualifying owner attestation, THE SYSTEM SHALL emit exactly
20 staged review entries and zero review events, owner attestations, `approved_exact` records or
authority-bundle records. It SHALL report `awaiting_owner_review_gate`, make no catalog mutation and
exit without claiming a passed Gate.

### T5E-R2 — Historical-to-current catalog bridge

WHEN a frozen CAR-T4 candidate is prepared for review, THE SYSTEM SHALL create an immutable
`CatalogResolutionBinding` rather than changing the frozen candidate. The binding SHALL include the
original candidate and proposal hashes, catalog-application-manifest hash, catalog-v2 raw hash,
candidate/release/family keys, applied UUID and applied catalog-record hash. It SHALL prove a
one-to-one match by candidate, proposed UUID, canonical ID and release key.

The review candidate is a derived `AuthorityCandidate` with the same candidate/source/family/release
identity, `catalog_lookup_state=existing_uuid`, the applied `canonical_uuid`, `status=staged`,
`synthetic=false` and `resolver_output_consulted=false`. Bundle validation SHALL use catalog-v2
records, not the obsolete pre-application proposal path, while retaining both historical hashes in
the parent-artifact chain.

### T5E-R3 — Output-blind review material

WHEN the preparation packet is built, EACH entry SHALL show the catalog-v2 identity and values,
six ordered source-to-catalog evidence rows (`casting`, `release_year`, `series`,
`collector_number`, `series_position`, `identifiers`), evidence references, source binding,
conflicts/shortfalls, explicit `color=null` and `edition=null`, publication limits and plain-language
owner questions. It SHALL contain no resolver candidate, predicted UUID, score or model output and
SHALL record `resolver_output_consulted=false` and `network_requests=0`.

### T5E-R4 — Two distinct owner Gates

WHEN an entry leaves `staged`, THE SYSTEM SHALL require an explicit owner review outcome bound to
the exact packet, catalog and entry. A successful first Gate creates `staged -> reviewed`; it does
not approve exact authority.

WHEN a reviewed entry becomes exact authority, THE SYSTEM SHALL require a fresh, explicit owner
decision whose declared scope is exact-authority approval. Only this second Gate creates
`reviewed -> approved_exact`. A navigation, continuation or catalog-application instruction SHALL
fail qualification for both Gates.

### T5E-R5 — Batch decisions remain exact and attributable

IF the owner reviews or approves more than one entry in one response, THE SYSTEM SHALL preserve one
private `BatchOwnerAuthorization` containing the exact external response, aware timestamp, public
role `project_owner`, intended transition, packet/catalog hashes, and the ordered covered entry
hashes. Each per-entry `OwnerAttestation` and `AuthorityReviewEvent` SHALL reference that batch
authorization SHA-256 and reproduce only the declared outcome and bounded non-sensitive reason.

The same batch response may bind multiple entries only when every covered entry is listed. It SHALL
not be represented as multiple independent utterances, extended to an unlisted row, reused for the
other Gate, or used after any bound input changes.

### T5E-R6 — Fail-closed transitions and bundle freeze

IF any evidence is incomplete/conflicting, an entry cannot identify one release, a binding is stale,
or output blindness was violated, THEN the entry SHALL become `held`, `conflicted` or `insufficient`
through a valid event and SHALL not count. Remediation SHALL require a fresh `reviewed` event.

WHEN final events are frozen, THE SYSTEM SHALL count only distinct non-synthetic
`approved_exact` records. The Gate is eligible only with at least 20 variants across at least four
families, with two releases per counted family; otherwise it SHALL publish exact shortfalls as
`blocked_insufficient_exact_authority`.

### T5E-R7 — Private/public split

WHEN CAR-T5 writes review material, THE detailed packet, exact owner responses, batch
authorizations and per-event attestations SHALL remain in a dedicated Git-ignored authority-review
workspace with owner-only permissions. Its exact ignore rule SHALL be installed and verified before
the first private file is written. Tracked artifacts SHALL contain no owner verbatim or private
identity and only the minimum candidate/event metadata, irreversible hashes, counts, aggregates,
attribution and public role required by CAR-R6.

### T5E-R8 — Determinism, atomicity and replay

WHEN any preparation, event or bundle artifact is frozen, THE SYSTEM SHALL use canonical JSON,
stable packet/family/entry order, complete parent hashes, one trailing newline, temporary-file
validation and atomic replacement. A `--check` replay SHALL return `unchanged`; stale, partial,
duplicate, reordered or checksum-inconsistent input SHALL fail before any tracked or private output
is replaced.

## 4. Review payload and batching

The packet contains 20 entries in the already frozen packet order. The owner-facing presentation is
grouped into seven family batches (six batches of three releases and one batch of two releases).
Family grouping keeps near-duplicate releases adjacent and already exceeds the four-family minimum;
it does not pre-approve any row.

Each family batch displays:

1. packet, catalog, application-manifest and family-batch hashes;
2. the ordered candidate ID, release key, canonical UUID and catalog-record hash for each entry;
3. the six supported field comparisons plus null color/edition constraints;
4. any conflict/shortfall and the output-blindness declaration;
5. a first-Gate question asking for `reviewed`, `held`, `conflicted` or `insufficient` per covered
   entry.

After all 20 entries reach `reviewed`, the system produces a deterministic reconciliation summary
with 20 entries, seven families and zero unresolved conflicts. Only then may it ask a separate
second-Gate question for `approved_exact` or a non-approved outcome. The owner may answer per family
or in one 20-entry batch, but the response must explicitly name the exact-authority scope and bind
the presented packet/batch identity. Silence, an ambiguous acknowledgement or a general request to
continue is not a decision.

## 5. Artifacts and contracts

### Preparation stage — next executable task

Private, Git-ignored:

- `data/authority-review/canonical-authority-review-v1/local-authority-review-v1/authority-review-packet.json`
- `data/authority-review/canonical-authority-review-v1/local-authority-review-v1/OWNER-REVIEW.md`

Tracked, safe:

- `data/authority-review/canonical-authority-review-v1/authority-review-packet-manifest.json`

The safe manifest records schema/status, the immutable input hashes, 20 entries, seven families,
family batch sizes, six evidence rows per entry, 20 null colors, 20 null editions, zero events,
zero exact approvals, resolver-output/network counters, private packet SHA-256 and next Gate. It
contains no product rows, questions or owner response.

Required implementation surfaces:

- add the exact private workspace path to `.gitignore` before packet materialization;
- extend the authority-review contract with
  `pvr-canonical-authority-catalog-resolution-binding-v1`,
  `pvr-canonical-authority-batch-owner-authorization-v1`,
  `pvr-canonical-authority-owner-attestation-v2` and
  `pvr-canonical-authority-review-event-v2`; the two v2 contracts add an explicit
  `batch_authorization_sha256` while preserving every v1 packet/catalog/event binding;
- define `pvr-canonical-authority-review-packet-v1` and
  `pvr-canonical-authority-review-packet-manifest-v1` for the private packet and safe manifest;
- add a dedicated CAR-T5 preparation/record/freeze CLI rather than changing the CAR-T4 packet
  builder's frozen behavior;
- add focused authority tests for reconciliation, privacy, transitions and deterministic replay.

### Decision and freeze stage — blocked on owner Gates

Private, Git-ignored inputs:

- `batch-owner-authorizations.json`
- `owner-attestations.json`

Tracked outputs remain those named by CAR-T5 in `tasks.md`:

- `authority-candidates.json`
- `review-events.json`
- `approved-authority.json`
- `authority-manifest.json`

Public review events reference private authorization/attestation hashes but never include exact
owner text. `approved-authority.json` and `authority-manifest.json` are not created as passing
artifacts until the second Gate is complete; a non-qualifying run emits the defined blocked status
and exact shortfalls.

## 6. Atomic tasks and Gates

### CAR-T5P — Prepare exact-authority review `[backend -> qa -> doc_curator]`

1. Implement the catalog-resolution and preparation contracts without changing CAR-T4 artifacts.
2. Build the 20-entry local packet and safe preparation manifest atomically.
3. Run focused positive/negative tests and two `--check` replays.
4. Verify the working diff contains no catalog, CAR-T4 decision, authority event or bundle change.
5. Present the seven output-blind family batches and stop at **Owner Gate T5-G1**.

CAR-T5P is the smallest safe next executable task. It can be implemented under the current
instruction because it records no human outcome.

### Owner Gate T5-G1 — Human review

The owner must explicitly provide an outcome for every covered entry against the frozen packet. A
successful result produces append-only `staged -> reviewed` events. Any other explicit outcome is
recorded without counting the entry. After event capture and replay verification, present the
20-entry reconciliation summary and stop.

The final Batch 1 path is deliberately non-sequential: it may run only after the complete recorded
Batches 2–7 state. This allows the previously deferred Mazda Autozam family to close the first Gate
without weakening predecessor validation. A generic continuation instruction does not materialize
the batch; the exact owner response must explicitly bind Batch 1, its three toy identifiers, the
`reviewed` outcome, null `color`／`edition`, and the exclusion of `approved_exact` and RHB-T5.

T5-G1 is now complete: all seven family batches produced 20 reviewed events with zero staged
entries. That completion did not itself authorize exact authority or RHB work. T5-G2 now advances
only through separately scoped owner outcomes, beginning with the independently recorded Batch 1.

### Owner Gate T5-G2 — Exact-authority approval

The owner must separately authorize `approved_exact` for the exact reviewed scope. Successful
entries receive `reviewed -> approved_exact`; failures remain traceable and excluded. This Gate does
not authorize RHB-T5.

Batch 1 is complete: its three Mazda Autozam entries are `approved_exact`, while the other 17
entries remain `reviewed`. The exact decisions cover only the six supported snapshot fields;
`color` and `edition` remain null. The next executable action is another fresh, family-bounded
T5-G2 decision. CAR-T5F cannot start until all remaining outcomes are recorded and reconciled.

### CAR-T5F — Freeze bundle `[task_executor -> qa -> doc_curator]`

After T5-G2, validate all parents and event chains, freeze safe tracked outputs, run two unchanged
checks, and report either `eligible_for_rhb_t4_reaudit` or exact shortfalls. The next possible stage
is only CAR-T6, a fresh versioned RHB-T4 re-audit.

## 7. QA acceptance

CAR-T5P passes only when:

- catalog/application inputs match the immutable hashes and the catalog is 140/120/20;
- exactly 20 historical candidates resolve one-to-one to 20 distinct catalog-v2 UUIDs, canonical
  IDs and release keys across seven families;
- each entry has exactly six complete agreeing evidence rows, `color=null` and `edition=null`;
- the private packet is output-blind and the safe manifest contains no product row or owner text;
- events, attestations, `approved_exact`, authority records and RHB changes all remain zero;
- interrupted writes preserve prior artifacts and two `--check` runs return `unchanged`.

Negative tests must reject at least: generic continuation as approval; catalog-application
authorization reuse; direct `staged -> approved_exact`; one response reused across both Gates;
missing/reordered/extra batch entries; stale catalog/application/packet/record hashes; duplicate
UUID, canonical ID or release key; non-null/inferred color or edition; `variant_note` promoted to a
supported value; missing/conflicting evidence; resolver output consultation; false second-reviewer
claims; public owner verbatim/PII; partial writes; and any RHB-T5 mutation.

## 8. Recovery and unresolved owner decisions

Preparation is recoverable by discarding only temporary files; frozen CAR-T4 and catalog-v2 inputs
remain unchanged. Review corrections are new append-only events, never edits. An erroneous exact
approval is revoked by a new event; dependent counts and manifests become invalid until rebuilt.

The following decisions remain exclusively with the owner:

1. fresh T5-G2 exact-authority outcomes for the remaining 17 reviewed entries;
2. the disposition/remediation of any held, conflicted or insufficient entry;
3. any later authorization to freeze CAR-T5F or run CAR-T6; RHB-T5 remains a still later, separate
   Gate.
