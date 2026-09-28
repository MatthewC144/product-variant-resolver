# Canonical Authority Review v1 — Source approval

Date: 2026-09-28. Mode: Lite / Lean Industrial. Owner Gate:
**PASSED FOR ONE EXISTING SNAPSHOT REVIEW ONLY**.

## What this Gate approves

The project owner approved offline reuse and later human review of exactly one artifact already
checked into this repository:

- source ID: `fandom-hot-wheels-2025-pilot-r790665-v1`
- source kind: `licensed_community_snapshot`
- claim tier: `community_reference_snapshot_exact`
- page: `List of 2025 Hot Wheels`
- frozen page URL:
  `https://hotwheels.fandom.com/wiki/List_of_2025_Hot_Wheels?oldid=790665`
- revision: `790665`, timestamp `2026-07-17T05:50:26Z`
- artifact: `data/external/hot-wheels-wiki/pilot-2025/normalized.json`
- artifact SHA-256: `e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6`
- 100 unique `source_record_id` values, bound by a canonical-set SHA-256 in the decision manifest

`community_reference_snapshot_exact` means that a later owner-reviewed value may be exact relative
to this frozen community Wiki revision. It does **not** mean Mattel/manufacturer-certified truth.
This Gate permits records to enter the CAR review process; it does not approve a canonical UUID,
create an `approved_exact` record, satisfy the 20-variant/four-family target, or unlock RHB-T5.

## Rights, attribution and access boundary

The existing normalized text derivative is reused under its recorded CC-BY-SA terms. Every future
review row must retain the page title, frozen URL, revision, revision timestamp,
`source_record_id`, normalized artifact checksum, license URL and attribution/share-alike notice.
Attribution is to Hot Wheels Wiki contributors for the named page and revision, with a note that
the repository contains a normalized derivative.

Current Fandom terms restrict unauthorized automated access. Permission for the historical
automated access that produced this local artifact has **not** been established, and this owner
decision does not claim that Fandom authorized that access. The decision is limited to reuse of the
existing checked-in normalized text snapshot. It authorizes zero network requests, browser
automation, new page retrieval, API access, Selenium/crawling, raw-page acquisition, image/media
download or OCR. The checked-in `raw.json` is not an approved CAR input.

## Allowed fields and mapping

Later review may use only these snapshot-to-authority mappings:

| Snapshot field | Review meaning | Restriction |
|---|---|---|
| `casting_name` | `casting` | Must remain bound to the row evidence. |
| `release_year` | `release_year` | No inference beyond the frozen row. |
| `series` | `series` | No inference beyond the frozen row. |
| `collector_number` | `collector_number` | Preserve as text. |
| `series_position` | `series_position` | Preserve as text. |
| `toy_number` | `identifiers` | Treat as a source identifier, not a generated UUID. |
| `variant_note` | review context only | May describe the row but cannot invent another field. |

All 100 snapshot rows have `color=null`. Color must remain unknown unless a separately approved
source supplies explicit evidence. In particular, `variant_note="2nd Color"` states that another
color release exists; it does not identify the color and cannot be converted into a color name.
`edition` may be reviewed only when an approved source row contains explicit, non-empty edition
evidence. This snapshot currently supplies no edition mapping, so none may be invented.

## Review and publication boundary

- Public reviewer identity is the role `project_owner` only; private name/contact/account data is
  prohibited.
- Later confirmation method is `owner_attestation`; completion of a form never auto-approves a row.
- Resolver/model outputs, candidates, scores and predicted UUIDs are forbidden during review and
  must be recorded as not consulted.
- The existing normalized text artifact, source decision, license/attribution metadata, hashes,
  counts and safe aggregates may remain public in Git.
- Detailed owner packets and unrelated private evidence remain local-only and outside Git.
- No authority rows are created by CAR-T1.

## Other sources

The 1,763-row workbook remains `family_context` / `candidate_selection_only`. It was assembled from
third-party material but is not individually bound to a Wiki page revision, attribution record and
source checksum, so it cannot establish an exact field or canonical UUID. Every other existing or
future source is held/rejected for CAR exact review until a separate owner decision establishes its
rights, checksum and permitted scope.

## Feasibility is not authority

Offline inspection of the approved snapshot found 100 rows, 38 casting families with at least two
rows, 85 rows inside those families, and zero missing values for `toy_number`, `casting_name`,
`release_year`, `series`, `collector_number` and `series_position`. All 100 rows lack color.

These figures are `candidate_feasibility_not_authority`. They indicate that CAR-T3 may propose a
review queue; they do not prove any exact variant, any canonical UUID, the 20/4 target, or benchmark
readiness.

## Gate result

Gate status is `passed_for_single_existing_snapshot_review`. The next permitted task is CAR-T2,
which implements strict contracts. CAR-T3 and later owner review remain separate Gates. Network
collection, authority rows, RHB changes, query/label authoring and RHB-T5 remain prohibited.
