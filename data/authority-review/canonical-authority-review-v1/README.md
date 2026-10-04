# Canonical Authority Review v1 artifact boundary

This directory contains the public, Git-safe artifacts for Canonical Authority Review (CAR) v1.
The workflow has completed CAR-T5F and frozen a 20-record authority bundle. It still provides no
permission to begin RHB-T5.

## Current state

- CAR-T1 approved human review of one existing normalized 100-row text snapshot only:
  `fandom-hot-wheels-2025-pilot-r790665-v1`, Wiki revision `790665`.
- Its maximum claim is `community_reference_snapshot_exact`: exact relative to that frozen
  community-reference revision after owner review, not manufacturer-certified truth.
- The source decision and manifest remain the source of truth for permission, attribution,
  publication, revision, checksum, and the exact 100-row membership set.
- CAR-T2 supplies an offline validation layer in
  `src/product_variant_resolver/canonical_authority_review.py` and hand-built synthetic tests. It
  deliberately imports the CAR-T1 Gate validator instead of copying or weakening its rules.
- CAR-T5F freezes 20 distinct `approved_exact` variants across seven qualifying families. The Gate
  result is `eligible_for_rhb_t4_reaudit`, with zero variant/family shortfall. Exactness remains
  relative to the frozen community snapshot, not Mattel/manufacturer-certified truth.
- The fresh CAR-T5F owner authorization remains in the ignored private workspace. Public
  `approved-authority.json` and `authority-manifest.json` contain only bounded identities, hashes,
  counts, composition and role metadata; CAR-T6 and RHB-T5 remain false.

## Contract flow

1. `validate_authority_source_decisions(root)` revalidates the checked-in CAR-T1 artifacts and
   frozen parent files before exposing the approved record-ID set.
2. `AuthorityCandidate` can reference only one member of that set. Candidate context remains
   `candidate_selection_only`; it cannot carry resolver output or a predicted winner.
3. `VariantFieldEvidence` maps only approved snapshot fields. `toy_number` is the identifier
   source. Every CAR-v1 evidence row must bind the candidate's own fixed snapshot row and reproduce
   that row's source value; another valid row from the same 100-row set cannot be borrowed. The
   snapshot cannot establish color or edition, so missing color remains unknown. Catalog/reviewed
   values are recursively checked for contact, seller/account, credential and address data.
   Hash-bearing evidence lists use the declared `VariantField` order; reference/binding lists and
   catalog identifiers are sorted and unique. A caller cannot produce a second digest for the same
   semantic set merely by reversing a list.
4. `FrozenCatalogParent` preserves the repository catalog's `catalog_version` plus `products[]`
   shape and binds each UUID to a canonical record and record SHA-256. Version and catalog hash are
   derived from that one strict parent; callers cannot supply a separate trusted version/hash.
   Existing-UUID review proves exact membership. A missing UUID must go through a separately
   reviewed `CatalogRecordProposal` whose parent version/hash matches, while its new UUID must not
   already be a parent member. Catalog approval does not approve authority.
5. `OwnerReviewPacket` is local-only and output-blind. It reuses the same frozen catalog parent (or
   separately approved proposal), derives its version/hash, and computes required evidence from
   every non-empty product field. Partial packets must enumerate every `missing:<field>` and
   `conflicting:<field>` marker exactly, in sorted unique order, and still ask a plain-language
   owner question. Its strict
   companion proves that resolver candidates, predicted UUIDs, model scores, network collection,
   and PII are absent.
6. `AuthorityReviewEvent` is append-only. The only transitions are:

   - `staged → reviewed | held`
   - `held | conflicted | insufficient → reviewed`
   - `reviewed → approved_exact | conflicted | insufficient | held`
   - `approved_exact → revoked`
   - `revoked` is terminal

   Every event uses an aware timestamp, public role `project_owner`, `owner_attestation`, a nonblank
   reason, packet/catalog hashes, and `resolver_output_consulted=false`. A complete form never
   auto-promotes itself.
7. `validate_authority_bundle` receives the candidates, catalog records or separately approved
   proposals, complete event chains, attestations, packet hashes, frozen catalog parent and CAR-T1
   root. It runs the same candidate/proposal/review validators for every bundle row, reconstructs
   the exact ordered parent digest set, and verifies each evidence checksum against the latest
   event. Events must use canonical `(candidate_id, reviewed_at, event_id)` ordering. It then
   recomputes effective status counts, distinct exact variants, qualifying families,
   and 20-variant/four-family shortfalls. Truncated histories and revoked, held, conflicted,
   insufficient, duplicate, or synthetic rows cannot pad the Gate.
8. `canonical_authority_freeze.py` revalidates the real two-Gate event chain, private attestations,
   latest-event links, permissions and source/catalog parents. It requires a fresh CAR-T5F response,
   installs the private authorization plus two public outputs atomically, and replays byte-identically.

Catalog products are also bound to the candidate's exact family and proposed release keys.
High-level validators re-parse nested Pydantic values from their JSON representation. This matters
because a caller must not bypass validation by handing the workflow a preconstructed model.

## Public versus local artifacts

Git may contain these contracts, tests, existing normalized text, attribution/license metadata,
irreversible SHA-256 values, status counts, aggregates, and later owner-approved safe records.
Detailed review packets and unrelated evidence remain in an owner-configured Git-ignored location.
Public metadata rejects obvious email/phone data and unsafe parent references such as absolute paths
or `..` traversal.

The workflow performs no HTTP, browser, Selenium, resolver, FastAPI, model, or database work.
The original CAR-T2 contract module remains read-only; the CAR-T5F builder uses validated temporary
files, atomic replacement and rollback so a partial artifact cannot be promoted.

## What comes next

The next possible stage is CAR-T6: a fresh, versioned RHB-T4 re-audit that independently validates
the bundle. CAR-T5F does not force that audit to pass, does not authorize RHB-T5 and does not prove
resolver, RAG, embedding or benchmark quality.
