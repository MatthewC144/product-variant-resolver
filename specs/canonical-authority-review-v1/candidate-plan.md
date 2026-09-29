# CAR-T3 Candidate Plan — Owner Approved

Drafted: 2026-09-28. Owner approval recorded: 2026-09-29T13:26:17Z. Mode: Lite / Lean
Industrial. Status: **OWNER APPROVED**.

## What this plan does—and does not do

This plan chooses a small group of rows from the already approved, fixed 100-row Hot Wheels Wiki
snapshot for the later manual review packet. The owner approved this queue and its output-blind
review method. A **candidate** is still only a row worth reviewing. It is not yet a correct product
variant, does not have an approved canonical UUID, and does not count toward the 20-variant/four-
family authority Gate.

The plan uses the source's casting label only to group review work. It does not treat that label—or
any source value—as verified truth. Color remains unknown. Phrases such as `2nd Color`, `3rd Color`,
`Zamac`, and `Red Edition` are review warnings only; they are not used to infer a color, edition, or
exact release.

## Deterministic selection rule

The same fixed snapshot produces the same queue:

1. Keep only families with at least two rows whose `source_record_id`, `toy_number`, casting label,
   year, series, collector number, and series position are non-empty. This is a workload-quality
   check, not verification of those values.
2. Prefer every three-row family whose rows remain in one source series. Sort family labels without
   regard to letter case and sort rows by `source_record_id`. This yields six families and 18 rows.
3. Fill the minimum target with the eligible two-row, single-series family that appears earliest in
   the frozen source order. This adds Mazda MX-5 Miata and reaches exactly 20 primary candidates.
4. Keep the remaining three-row families as a separate surplus queue. Their cross-series or special-
   release context makes them useful fallbacks but more complex first-review choices. Surplus rows do
   not count toward the primary target.

The 1,763-row workbook, resolver results, predicted UUIDs, scores, and model output were not used.

## Approved primary queue

| Candidate family label | Candidate rows | Why it is in the primary queue | Review warning |
|---|---:|---|---|
| `'21 Ford Bronco` | 3 | Complete selection keys; three rows in one source series | `2nd/3rd Color` wording is context only |
| `Draftnator` | 3 | Complete selection keys; three rows in one source series | `2nd/3rd Color` wording is context only |
| `Mazda Autozam` | 3 | Complete selection keys; three rows in one source series | `Zamac` and color-order wording cannot fill edition or color |
| `Morgan Super 3` | 3 | Complete selection keys; three rows in one source series | `2nd/3rd Color` wording is context only |
| `Nissan Skyline 2000GT-R LBWK` | 3 | Complete selection keys; three rows in one source series | `2nd/3rd Color` wording is context only |
| `Subaru BRZ` | 3 | Complete selection keys; three rows in one source series | `Zamac` and color-order wording cannot fill edition or color |
| `Mazda MX-5 Miata` | 2 | Deterministic two-row fill needed to reach the minimum 20 | `2nd Color` wording is context only |

Primary total: **20 candidate rows across seven proposed families**. This exceeds the family planning
minimum but does not yet establish any approved exact variant.

## Surplus fallback queue

| Candidate family label | Candidate rows | Why it is surplus | Review warning |
|---|---:|---|---|
| `'90 Honda Civic EF` | 3 | Remaining complete three-row family | Rows span normal and Red Edition source context |
| `Lamborghini Huracán Sterrato` | 3 | Remaining complete three-row family | Rows span Safari Mode and Red Edition source context |
| `Small Bloc` | 3 | Remaining complete three-row family | Rows span HW Metro and Red Edition source context |

Surplus total: **9 rows across three families**. These are fallback work only. They cannot pad the
20-row primary queue, and moving one into primary later requires an explicit owner decision.

## Approved review method

- Reviewer role published in artifacts: `project_owner`.
- Confirmation method: `owner_attestation`.
- Resolver/model output remains hidden and `resolver_output_consulted=false`.
- CAR-T4 performs catalog lookup. Every candidate is currently
  `catalog_lookup_status=pending_car_t4`, with no canonical UUID supplied or inferred.
- Later packet review must preserve `color=null` unless separately approved explicit evidence exists.
- This plan approval only approves the queue and method. It does not approve catalog changes,
  evidence values, exact authority, RHB-T4, or RHB-T5.

## Owner decision recorded

At `2026-09-29T13:26:17Z`, the `project_owner` approved:

1. The seven-family, 20-row primary queue for CAR-T4 packet preparation.
2. The three-family, nine-row surplus queue as fallback only.
3. `project_owner` + `owner_attestation` as the review method while resolver/model output
   stays hidden.
4. The boundary that source labels and special-release phrases remain unverified context; color,
   edition, canonical UUIDs, and exact authority are still unset.

The owner message explicitly approved the CAR-T3 candidate plan. Its separate GitHub push
authorization is operational and outside this data-authority Gate. No additional decision reason is
inferred. CAR-T3 is closed; CAR-T4 remains not started until it is executed as its own task.
