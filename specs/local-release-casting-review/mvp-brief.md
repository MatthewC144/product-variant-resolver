# Local release casting review queue — MVP brief

Date: 2026-09-17. Mode: Lite / Lean Industrial. Status: **complete**.

Owner authorization: 「繼續下一步」 follows the completed local release staging milestone. This
authorizes the next offline review step over the existing owner-supplied snapshot. It does not
authorize network collection, automatic canonical promotion, color inference, or publication of
the 1,763 source rows or their casting labels.

## Purpose

Turn 1,763 staged release observations into a deterministic, family-level human review queue. The
queue compares exact normalized brand/casting keys with the synthetic canonical fixture and the
non-canonical human-backed draft. A match is only a review candidate; every cluster remains held.

## Observable requirements

- **LCR-R1 — Offline fixed inputs.** WHEN the queue is built, THE SYSTEM SHALL read the validated
  local release snapshot plus the two repository catalogs and SHALL perform zero network requests.
- **LCR-R2 — Preserve review authority.** IF any staged row already has a canonical UUID, is not
  `needs_canonical_review`, is runtime-eligible, or has a non-null color, THEN THE SYSTEM SHALL fail.
- **LCR-R3 — Review clusters, not asserted families.** WHEN labels are grouped, THE SYSTEM SHALL use
  a documented normalized brand/casting key, preserve every original label and source record ID in
  the private queue, and call the result a review cluster rather than a canonical family.
- **LCR-R4 — Exact candidates only.** WHEN catalogs are compared, THE SYSTEM SHALL classify exact
  normalized matches in both sources, the canonical fixture only, the human draft only, or neither;
  fuzzy matching SHALL NOT create review truth.
- **LCR-R5 — No promotion.** WHEN a candidate exists, THE SYSTEM SHALL keep `promotion_eligible=false`,
  `canonical_uuid=null`, and `hold_for_human_review`; exact text SHALL NOT approve a variant.
- **LCR-R6 — Surface normalization collisions.** WHEN more than one raw label collapses to one
  normalized key, THE SYSTEM SHALL retain all labels and flag the cluster for human alias review.
- **LCR-R7 — Deterministic and privacy-bounded artifacts.** WHEN identical inputs are reviewed, THE
  SYSTEM SHALL reproduce the same queue and checksum. The complete queue SHALL remain gitignored;
  the public report SHALL contain only hashes and aggregate counts, never source rows or labels.
- **LCR-R8 — Honest reporting.** WHEN results are reported, THE SYSTEM SHALL distinguish raw casting
  labels, normalized review clusters, candidate classes, observations, approved links, promotions,
  and reviewed colors. Candidate counts SHALL NOT be called verified catalog coverage.

## Design

```text
validated local staging snapshot (1,763 rows)
  + synthetic canonical fixture
  + human-backed review draft
  -> exact normalized brand/casting indexes
  -> 676 private review clusters with source-row references
  -> private deterministic queue (gitignored)
  -> public aggregate manifest/report (no labels or rows)
```

Normalization uses Unicode NFKD, ASCII folding, casefolding, and alphanumeric token boundaries. It
is suitable for candidate grouping, not identity approval. The queue records catalog candidate IDs
so a reviewer can inspect them locally, but the public artifact exposes only aggregate class counts
and the private queue hash. No SQL table, API response, RAG corpus, evaluation label, or catalog file
is changed by this step.

## Error handling and security boundary

Malformed catalogs, missing records, blank normalized keys, duplicate source IDs, changed staging
authority fields, existing canonical links, or non-null colors fail closed. Symlink output paths and
unexpected bundle files are rejected. Original XLSX, normalized source rows, raw casting labels, and
the complete queue remain outside Git. This workflow does not infer color from variant notes, URLs,
images, or catalog candidates.

## Testing strategy

Portable synthetic tests cover all four candidate classes, multiple products within one fixture
family, normalized-label collisions, deterministic order/hash, privacy-safe public output, and each
authority rejection. A local-owner-data integration checks the exact aggregate counts and skips with
an explicit reason when the unpublished snapshot is absent. Focused and full repository tests plus
changed-file Ruff/format and `git diff --check` must pass.

## Tasks

- [x] **LCR-T1** Implement deterministic review-cluster construction and exact candidate indexing.
  _(→LCR-R1–R6)_
- [x] **LCR-T2** Add the local/private bundle plus public aggregate manifest/report and CLI.
  _(→LCR-R7–R8)_
- [x] **LCR-T3** Add portable and owner-data tests, run QA, and update decision/evidence/log docs.
  _(→LCR-R1–R8)_

## Acceptance

The current owner snapshot produces 1,763 observations, 678 raw casting labels, 676 normalized
review clusters, and two normalization-collision clusters. Exact candidate counts are reported by
source, but approved links, canonical promotions, and reviewed colors remain zero. No private label
or source row is present in the committed public artifacts.
