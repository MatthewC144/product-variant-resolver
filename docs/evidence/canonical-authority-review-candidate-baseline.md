# Canonical Authority Review v1 — Candidate Baseline

Drafted: 2026-09-28. Owner approval recorded: 2026-09-29T13:26:17Z. Scope: CAR-T3 evidence.
Result: **CANDIDATE QUEUE OWNER APPROVED; EXACT AUTHORITY STILL ZERO**.

## Evidence boundary

The only row input inspected was the checked-in `normalized.json` for
`fandom-hot-wheels-2025-pilot-r790665-v1`, revision `790665`, SHA-256
`e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6`. Candidate membership was
checked against its fixed 100 `source_record_id` values and the CAR-T1 source decision. No network,
browser, resolver, model output, or 1,763-row workbook values were used.

This evidence proves that a lawful review queue can be formed and records the owner's approval of
that queue and its output-blind review method. It does not verify a source field, approve a UUID, or
create exact authority.

## Recomputed selection evidence

| Check | Result | Meaning |
|---|---:|---|
| Fixed snapshot rows | 100 | Membership universe only |
| Multi-release source-label groups | 38 | Candidate feasibility only |
| Rows within those groups | 85 | Candidate feasibility only |
| Primary owner-approved families | 7 | Exceeds the four-family planning minimum |
| Primary candidate rows | 20 | Meets the queue-size target exactly |
| Surplus owner-approved fallback families | 3 | Not counted toward primary |
| Surplus fallback rows | 9 | Not counted toward primary |
| Unique candidate `source_record_id` values | 29 of 29 | No row duplication |
| Primary/surplus overlap | 0 | Fallback rows do not pad primary |
| Candidate IDs duplicated | 0 | Each planned review item is distinct |

For all 29 candidate rows, the selection keys `source_record_id`, `toy_number`, casting label,
release year, series, collector number, and series position were non-empty. This is a deterministic
selection-quality check only; it does not declare those values correct or verified.

## Deterministic policy check

- Six eligible three-row, single-series source-label groups were selected first in case-insensitive
  label order, with records ordered by `source_record_id`; total: 18 rows.
- The earliest eligible two-row, single-series group in frozen source order filled the exact
  20-candidate target; total: two additional rows.
- All three remaining eligible three-row groups were placed in surplus because their rows span
  source series or special-release context; total: nine fallback rows.
- Re-running the rule against the unchanged snapshot reproduced the same 7/20 primary and 3/9
  surplus composition.

## Risks deliberately preserved for human review

- `2nd Color` and `3rd Color` are sequence context, not color names.
- `Zamac` is context and does not populate color or edition.
- `Red Edition` and cross-series groupings require explicit owner review; they do not prove exact
  release identity.
- Every candidate remains `catalog_lookup_status=pending_car_t4` and has `canonical_uuid=null`.
- Source family labels are grouping aids marked `candidate_selection_only`, not verified fields.

## Duplicate and shortfall result

There are no duplicate candidate IDs, duplicate source rows, or primary/surplus overlaps. The
candidate-plan shortfall is zero rows and zero families because the approved queue supplies 20
candidate rows across seven families. The authority shortfall is unchanged: **20 approved exact variants
and four qualifying families are still missing**. Surplus rows do not reduce that authority
shortfall unless they later pass catalog, evidence, output-blind owner review, and explicit approval
Gates.

## Telemetry and downstream state

- Network requests: `0`
- Browser sessions: `0`
- Resolver/model output consulted: `false`
- New raw pages/images/media acquired: `0`
- Canonical UUIDs approved by this plan: `0`
- Exact authority rows created by this plan: `0`
- CAR-T3 state: `owner approved at 2026-09-29T13:26:17Z`
- CAR-T3 approval scope: `primary 20 + surplus 9 + output-blind review method only`
- CAR-T4 and later tasks: `not started`
- RHB-T5 authorized: `false`
