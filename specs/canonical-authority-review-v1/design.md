# Canonical Authority Review v1 — Design

Date: 2026-09-26. Owner approval recorded: 2026-09-28. Mode: Lite / Lean Industrial. Status:
**IMPLEMENTED AND VERIFIED — VERSIONED RHB-T4 RE-AUDIT PASSED; RHB-T5 UNAUTHORIZED**.

This design defines a small upstream workflow. The owner approved only reuse and human review of the
existing checked-in normalized text snapshot `fandom-hot-wheels-2025-pilot-r790665-v1`; existing RHB
artifacts remain unchanged. The approval does not authorize any new scraping, network request, raw
page/image acquisition, or claim that the historical access method had Fandom permission.

## 1. Overview

The historical RHB-T4 passed engineering QA but correctly blocked the data Gate because no real
exact authority existed at that time. This workflow filled that gap without turning provisional
context or resolver output into truth, then preserved the blocked checkpoint beside a new versioned
RHB-T4 PASS.

It separates four decisions:

1. May the source be used for exact review?
2. Does a canonical product UUID exist, or must one be separately reviewed first?
3. Does the evidence support every populated release field?
4. Has the owner explicitly approved the record without viewing resolver/model output?

The lean target is 20 variants across four multi-release families. A blocked result is acceptable;
invented truth is not.

## 2. Architecture

```text
existing checked-in licensed community snapshot
                    |
             OWNER SOURCE GATE
                    |
    approved source decision + local digest
                    |
 local family context (candidate selection only)
                    |
           staged review queue
                    |
      local human-readable review packet
                    |
       canonical UUID exists?
          | yes             | no
          |          catalog proposal + OWNER APPROVAL
          +-----------------+
                    |
 complete field evidence + output-blind human review
                    |
        owner attestation (`project_owner`)
                    |
 reviewed -> approved / conflicted / insufficient
                    |
 deterministic authority bundle + safe manifest
                    |
           20 variants / 4 families?
             | yes                 | no
       fresh RHB-T4 audit     honest blocked result
```

Raw evidence and detailed packets stay in an owner-configured, Git-ignored directory. Git stores
contracts, safe metadata, hashes, counts, QA and documentation. No network component is introduced.

For CAR v1, the architecture's only exact-review input is the existing
`licensed_community_snapshot`; generic source branches remain fail-closed. Its maximum claim tier is
`community_reference_snapshot_exact`, meaning exact relative to frozen Wiki revision `790665` after
owner review, not Mattel/manufacturer-certified truth.

## 3. Frontend/backend boundaries

There is no UI, FastAPI or runtime-resolver change. Offline backend tooling owns schemas, packet
generation, transition validation, catalog proposals and deterministic bundle building. The owner
reviews readable Markdown/CSV plus strict JSON companions. QA owns adversarial verification;
documentation owns evidence, AI eval and the Project Log.

## 4. Tech assumptions

- Python, Pydantic strict models and canonical JSON follow the current RHB approach.
- SHA-256 binds versions and content; it does not grant permission or anonymize private data.
- The existing catalog remains the canonical UUID namespace.
- Local-only evidence is referenced through approved opaque IDs and hashes.
- The snapshot reuses CC-BY-SA text with attribution/share-alike and row-level binding to page,
  revision, `source_record_id` and normalized checksum.
- Current Fandom terms prohibit unauthorized automated scraping. CAR v1 does not perform new
  collection, and its reuse decision does not retroactively characterize historical access as
  authorized by Fandom.
- No browser, HTTP client, LLM labeling service or new database is needed.

## 5. Interfaces

The names are proposed; implementation may refine them without weakening contracts.

### 5.1 Source decision

```text
prepare-source-decision --source-metadata <local file> --output <draft>
validate-source-decision --decision <owner JSON> --evidence-root <local directory>
```

Preparation creates a blank packet and never grants permission. Validation checks the exact local
digest and every owner-completed use/publication field.

### 5.2 Candidate plan and review packet

```text
build-authority-review-packet \
  --source-decisions <approved decisions> \
  --catalog <frozen catalog> \
  --candidate-plan <owner-approved plan> \
  --local-evidence-root <local directory> \
  --output <local packet directory>
```

The candidate plan may use family context to choose work, but cannot prefill an exact UUID or verified
field from provisional/resolver output. The packet shows catalog values, evidence coverage, conflicts
and owner questions.

### 5.3 Catalog proposal

```text
prepare-catalog-record-proposal --review-entry <entry> --catalog <frozen catalog>
apply-approved-catalog-proposal --proposal <owner-approved proposal> --catalog <expected catalog>
```

Proposal generation is read-only. Applying a proposal requires a separate owner decision and commit,
and fails if the parent catalog changed. Creating a UUID does not approve its authority.

### 5.4 Review and bundle

```text
validate-review-entry --packet <packet> --entry <entry>
attest-review-entry --entry <reviewed entry> --attestation <owner attestation>
build-canonical-authority-bundle --reviews <events> --catalog <frozen catalog>
build-canonical-authority-bundle --check ...
```

Agreement/completeness never auto-approves. A separate event records the owner outcome. Bundle
success permits only a fresh RHB-T4 audit.

## 6. Data models

All models reject unknown fields and use versioned schemas.

### `AuthoritySourceDecision`

```text
source_id
source_kind                 licensed_community_snapshot
claim_tier                  community_reference_snapshot_exact
source_owner_or_controller
acquisition_method
access_limitation
local_evidence_sha256
allowed_fields[]
authority_use               approved | rejected | held
retention_scope             prohibited | local_only | public
publication_scope           prohibited | aggregate_only | public_rows
privacy_status              approved | rejected | pending
attribution_requirements[]
source_page / source_revision
decided_by_role / decided_at / decision_reason
```

CAR v1 permits only `fandom-hot-wheels-2025-pilot-r790665-v1`. Every row must bind page, revision
`790665`, `source_record_id`, checksum, CC-BY-SA attribution and share-alike. Approval for review does
not authorize new collection or imply manufacturer certification. A future source needs its own
owner decision and is outside this sequential implementation scope.

### `AuthorityCandidate`

```text
candidate_id / source_id / source_record_ref
source_page / source_revision / source_record_id / normalized_snapshot_sha256
family_group_key / proposed_release_key
selection_context_refs[]
selection_context_role      candidate_selection_only
catalog_lookup_state        existing_uuid | catalog_review_required
canonical_uuid              nullable until catalog review finishes
resolver_output_consulted   false
status                      staged | held
```

### `VariantFieldEvidence`

```text
field                        casting | release_year | series | color |
                             collector_number | series_position | edition | identifiers
catalog_value / reviewed_value
evidence_refs[] / source_ids[]
agreement                    agrees | conflicts | insufficient
notes
```

Every populated catalog field requires one evidence row. Empty optional values are not invented.
For this snapshot, `casting_name` maps to `casting`; `toy_number` maps to `identifiers`; supported
review fields are `release_year`, `series`, `collector_number`, `series_position` and
`variant_note`. Missing `color` remains `null`, and `2nd Color` is not a color-name inference.
The 1,763-row workbook is excluded from exact evidence and remains
`family_context` / `candidate_selection_only` because it lacks per-row revision, attribution and
checksum binding.

### `CatalogRecordProposal`

```text
proposal_id
parent_catalog_version / parent_catalog_sha256
proposed_canonical_uuid / proposed_product_record / product_record_sha256
source_decision_ids[] / field_evidence[]
review_status               staged | reviewed | approved | rejected
reviewed_by_role / reviewed_at / review_reason
```

Catalog approval and authority approval remain separate events and commits.

### `AuthorityReviewEvent`

```text
event_id / candidate_id
from_status / to_status
catalog_version / canonical_uuid / catalog_record_sha256
variant_field_evidence[] / source_decision_ids[]
confirmation_method         owner_attestation
attestation_sha256
resolver_output_consulted   false
reviewed_by_role / reviewed_at / review_reason
remediation_note            required for non-approved outcomes
```

Allowed transitions:

| From | To |
|---|---|
| `staged` | `reviewed`, `held` |
| `held`, `conflicted`, `insufficient` | fresh `reviewed` event after remediation |
| `reviewed` | `approved_exact`, `conflicted`, `insufficient`, `held` |
| `approved_exact` | `revoked` |
| `revoked` | none; create a new candidate/version |

For CAR v1, `reviewed_by_role` is the public role `project_owner`; no private reviewer identity is
published.

### `AuthorityBundleManifest`

```text
schema_version / bundle_version / authority_bundle_sha256
ordered_parent_artifacts[]  reference + SHA-256
catalog_version / catalog_sha256 / source_decision_sha256s[]
counts_by_status / approved_distinct_variant_count
qualifying_family_count / family_composition[]
resolver_output_consulted   false
network_requests            0
publication_scope
gate_status                 eligible_for_rhb_t4_reaudit |
                            blocked_insufficient_exact_authority
shortfalls / created_at
```

Only distinct, non-synthetic `approved_exact` records count. A qualifying family has at least two
different approved releases.

## 7. Gates

1. **Source Gate:** every evidence source has an approved exact-use decision.
2. **Candidate Gate:** owner approves the family/release queue; this does not establish truth.
3. **Catalog Gate:** every candidate resolves to one frozen UUID; missing records receive separate
   proposal approval and a separate commit.
4. **Review Gate:** complete field evidence plus `project_owner` attestation, followed by an explicit
   approval event.
5. **Bundle Gate:** at least 20 variants/four qualifying families, or exact shortfalls are published.
6. **RHB Gate:** a fresh RHB-T4 audit revalidates everything before RHB-T5 can be considered.

### CAR v1 approved starting state

- Input: existing checked-in `normalized.json` for source
  `fandom-hot-wheels-2025-pilot-r790665-v1` only, bound to page `List of 2025 Hot Wheels`, revision
  `790665`, and SHA-256 `e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6`;
  no new raw page or image.
- Candidate feasibility: 100 rows; 38 multi-release casting families; 85 rows inside those
  families; zero missing `toy_number`, casting, year, series, collector number or series position.
- Interpretation: feasibility for constructing a review queue only, not a 20-variant/four-family
  authority PASS.
- Reviewer: `project_owner`; confirmation: `owner_attestation`; resolver output remains invisible.
- Other context: the 1,763-row workbook may rank/select candidate families only.

## 8. Error handling

Errors identify the affected source/candidate without printing raw evidence:

| Error | Behavior |
|---|---|
| Missing/insufficient source rights | Hold dependent work; copy nothing. |
| Source outside approved fixed snapshot | Reject; require a new owner source decision. |
| Missing page/revision/record/checksum attribution | Hold; do not create exact evidence. |
| Missing color or `2nd Color` note | Preserve `color=null`; do not infer a color name. |
| Source/catalog checksum changed | Stop and rebuild/re-review against current parents. |
| UUID missing | Route to catalog proposal; never infer. |
| Field evidence incomplete/conflicting | Mark insufficient/conflicted; exclude from counts. |
| Invalid transition or entry mismatch | Reject; preserve the prior event chain. |
| Resolver output consulted | Invalidate the attempt; require fresh blind review. |
| PII/publication violation | Refuse output and identify only the field. |
| 20/4 shortfall | Freeze an honest blocked manifest. |
| Partial write | Keep the previous complete output; never promote temporary output. |

## 9. Security notes

- Treat exports, packets and review entries as untrusted structured input.
- Restrict evidence references to one configured local root; reject path traversal and escaping
  symlinks.
- Never log raw evidence, secrets, seller/account/contact details or proprietary rows.
- Run PII checks before public serialization and during QA.
- Keep credentials/cookies out of the workflow because no network acquisition exists.
- AI may help format artifacts, but cannot provide evidence or approve values.

## 10. Testing strategy

- Unit-test strict schemas, field coverage, state transitions, reviewer timestamps and counts.
- Negative-test missing permissions, stale parents, duplicate UUID/events, unsafe paths, PII,
  resolver-output consultation, invalid attestations, quota padding and revocation.
- Integration-test both existing-UUID and separately approved catalog-proposal paths.
- Verify deterministic `--check`, canonical ordering and atomic failure behavior.
- Prove CAR output cannot invoke/unlock RHB-T5 and only a fresh T4 audit decides the downstream Gate.
- Run existing RHB/catalog/API/resolver regressions, full pytest, Ruff, format, strict MyPy,
  compileall, JSON/hash/link checks, secret/PII scan and `git diff --check`.
- QA maps every requirement; AI eval tests grounding, authority, blindness, privacy and honest claims.

## 11. Lean delivery and portfolio value

The MVP uses repository-native files and one readable owner packet instead of building a labeling UI
or enterprise approval platform. It still demonstrates provenance, human-in-the-loop review,
catalog versioning, model-output independence, fail-closed states, privacy-aware publication and
reproducibility. The defensible portfolio story is that the system prevents provisional data or AI
predictions from manufacturing exact ground truth.
