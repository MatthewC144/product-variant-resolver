# Canonical Authority Review v1 — Requirements

Date: 2026-09-26. Owner approval recorded: 2026-09-28. Mode: Lite / Lean Industrial. Status:
**IMPLEMENTED AND VERIFIED — 20 EXACT VARIANTS / 7 QUALIFYING FAMILIES; RHB-T5 UNAUTHORIZED**.

This is an upstream plan for the blocked Representative Hard Benchmark v1. The owner approved reuse
and human review of the existing checked-in 100-row text snapshot
`fandom-hot-wheels-2025-pilot-r790665-v1`. This approval does not create a canonical UUID, authorize
new collection, claim that the historical access method had Fandom permission, or authorize RHB-T5.

## Product goal

Build a small, lawful, offline and human-reviewed process for establishing exact product variants.
The minimum successful result is at least 20 non-synthetic exact variants across at least four
same-casting, multi-release families. Each exact record must be independent of resolver/model output
and traceable to an approved source, a frozen catalog UUID, and complete release-level evidence.

At planning time, this addressed the evidence gap found by the historical RHB-T4 audit: the project
had 0 eligible exact variants and 0 eligible multi-release families. CAR v1 subsequently produced
20 approved exact variants across seven qualifying families and a new versioned RHB-T4 PASS. The
approved claim tier remains
`community_reference_snapshot_exact`: a human-reviewed value may be exact relative to that frozen
community-reference revision, but it is not Mattel/manufacturer-certified truth. Existing fixture
and Human Knowledge data remain context only. The 1,763-row workbook remains `family_context` /
`candidate_selection_only` because its rows are not individually bound to a Wiki revision,
attribution record and checksum.

## MVP scope

- Record the approved, tightly bounded reuse decision for the existing Wiki-derived snapshot.
- Select a small review queue using existing local family context only as a guide.
- Generate a readable local review packet and strict machine-readable records.
- Review existing canonical UUIDs or separately approve creation of missing catalog records.
- Freeze an approved authority bundle or an honest blocked result.
- Rerun RHB-T4 before any benchmark query or label work begins.

## Deferred / out of scope

- Crawling, Selenium, live APIs, marketplace/Fandom collection, OCR, or authentication automation;
  current Fandom terms prohibit unauthorized automated scraping, so this milestone performs zero new
  network access or collection.
- Automatic UUID inference, canonical promotion, conflict resolution, or AI-generated truth.
- Expansion beyond the minimum 20 variants/four families.
- RHB-T5, benchmark labels, resolver evaluation, model training, threshold tuning, or API changes.
- Publishing local-only evidence, seller/account details, contact information, or proprietary exports.

## Observable requirements

### CAR-R1 — Source rights and offline acquisition

WHEN a source is proposed, THE SYSTEM SHALL require an owner decision covering ownership/control,
acquisition method, exact-authority use, allowed fields, retention, publication, privacy,
attribution, claim tier, reviewer role, and evidence checksum. IF any decision is missing, pending,
or unsuitable for exact-authority use, THEN dependent records SHALL remain `held`. FOR CAR v1, THE
SYSTEM SHALL accept only the existing checked-in text snapshot
`fandom-hot-wheels-2025-pilot-r790665-v1`, identify its source kind as
`licensed_community_snapshot`, and limit its authority claim to
`community_reference_snapshot_exact`. THE SYSTEM SHALL bind every reviewed row to
`List of 2025 Hot Wheels`, revision `790665`, `source_record_id`, normalized snapshot checksum, and
CC-BY-SA attribution and share-alike obligations. WHILE this milestone runs, THE SYSTEM SHALL
perform zero network/browser collection and SHALL NOT describe the historical access method as
Fandom-authorized.

### CAR-R2 — Candidate context is separate from exact truth

WHEN a review queue is built, THE SYSTEM MAY use approved local family context only as
`candidate_selection_only`. WHEN a candidate is considered exact, THE SYSTEM SHALL require a
canonical UUID already present in the frozen catalog or created through a separate owner-approved
catalog review, plus the catalog version, product checksum, and evidence for every non-empty field:
`casting`, `release_year`, `series`, `color`, `collector_number`, `series_position`, `edition`, and
`identifiers`. Family labels, staging rows, nearest candidates and provisional values SHALL NOT fill
these fields or establish the UUID.

FOR the approved snapshot, THE SYSTEM SHALL map `casting_name` to `casting`, `toy_number` to
`identifiers`, and may review `release_year`, `series`, `collector_number`, `series_position`, and
`variant_note`. Missing `color` SHALL remain `null`; neither `variant_note` nor a phrase such as
`2nd Color` SHALL be used to infer a color name. The 1,763-row workbook SHALL remain
`family_context` / `candidate_selection_only` and SHALL NOT establish an exact value or UUID.

### CAR-R3 — Output-blind owner packet

WHEN candidates are ready, THE SYSTEM SHALL create a human-readable local packet showing catalog
values, field-by-field evidence references, missing/conflicting items, publication limits and plain-
language owner questions. It SHALL have a strict machine-readable companion, hide resolver/model
candidates, scores and predicted UUIDs, and record `resolver_output_consulted=false`.

### CAR-R4 — Human approval and state control

WHEN a candidate is reviewed, THE SYSTEM SHALL use append-only events and allow only controlled
transitions: `staged` → `reviewed` or `held`; `reviewed` → `approved_exact`, `conflicted`,
`insufficient`, or `held`; remediated non-final records → a fresh `reviewed` event; and
`approved_exact` → `revoked`. Approval SHALL require either double-entry reconciliation or explicit
owner attestation bound to the packet/catalog checksums, reviewer role, aware timestamp and reason.
CAR v1 SHALL use `confirmation_method=owner_attestation` and the public reviewer role
`project_owner`. The workflow SHALL NOT auto-promote a complete form or falsely claim a second human
reviewer.

### CAR-R5 — Conflict and blindness fail closed

IF evidence conflicts, is incomplete, has uncertain rights, uses a stale reference, cannot identify
one exact release, or was reviewed with resolver/model output, THEN the candidate SHALL be
`conflicted`, `insufficient`, or `held` with a reason and remediation note. It SHALL NOT enter exact
counts until a fresh valid review and explicit approval occur.

### CAR-R6 — Private evidence and safe public artifacts

WHEN artifacts are written to Git, THE SYSTEM SHALL include only schemas/code, the already checked-in
normalized 100-row text snapshot, CC-BY-SA attribution/share-alike metadata, approved non-sensitive
decision metadata, irreversible hashes, counts and aggregates. No new raw page, image or media asset
SHALL be acquired or added. Local evidence and detailed review packets SHALL remain outside Git.
Email, phone, seller/account identity, credentials, addresses and unrelated personal data SHALL be
rejected from public metadata and evidence references.

### CAR-R7 — Deterministic freeze and revocation

WHEN a packet, catalog proposal, event set or authority bundle is frozen, THE SYSTEM SHALL use stable
ordering, canonical JSON, atomic writes, schema/version, complete parent SHA-256 values, counts,
family composition and reviewer metadata. An unchanged rebuild SHALL be byte-identical or return
`unchanged`; stale, partial, reordered or checksum-inconsistent input SHALL fail closed. WHEN an
approved record is revoked, dependent counts/manifests SHALL be invalidated while history remains.

### CAR-R8 — Minimum composition and honest result

WHEN the bundle is evaluated, THE SYSTEM SHALL count only distinct, non-synthetic `approved_exact`
variants and SHALL require at least 20 variants across at least four families, with at least two
different approved releases in each counted family. Duplicates, aliases and repeated evidence events
SHALL NOT pad counts. IF either minimum is missed, THEN the result SHALL be
`blocked_insufficient_exact_authority` with exact shortfalls, not a passed data Gate.

### CAR-R9 — RHB handoff boundary

WHEN CAR v1 finishes, THE PROJECT SHALL output an authority candidate bundle and approved-authority
artifact for a new RHB-T4 audit. It SHALL NOT overwrite the previous RHB audit in place, begin
RHB-T5, create benchmark queries/labels, or claim benchmark readiness. Only a fresh RHB-T4 audit may
reopen the downstream Gate.

### CAR-R10 — Regression and negative verification

WHEN implementation is verified, THE PROJECT SHALL test missing permissions, invalid transitions,
stale hashes, absent UUIDs, incomplete fields, duplicate/quota padding, output consultation, PII,
publication leakage, revocation and partial writes, while preserving current RHB, catalog, resolver
and API behavior.

### CAR-R11 — QA and documentation

WHEN the milestone closes, THE PROJECT SHALL publish requirement-mapped QA, deterministic evidence,
an AI-eval rubric for grounding/authority/blindness/privacy/honesty, and a narrative Project Log
covering the problem, changes, technical decisions, failures/fixes and remaining Gate. Engineering
PASS and the data result SHALL be reported separately.

## Recorded owner decision and remaining owner Gates

The owner approved sequential implementation using only
`fandom-hot-wheels-2025-pilot-r790665-v1`, with reviewer role `project_owner` and confirmation method
`owner_attestation`. Local inspection found 100 normalized rows, 38 casting families with multiple
releases, and 85 rows within those families. `toy_number`, casting, year, series, collector number
and series position each have zero missing values. These figures establish candidate feasibility
only; they do not satisfy the 20-variant/four-family authority Gate.

The sequential family/release, catalog, review, exact-authority, freeze and CAR-T6 Gates are now
complete. No later Gate may broaden the source or collection scope without a new source decision.
RHB-T5, query-pack authoring and label authoring remain outside CAR v1 and require a separate owner
authorization.
