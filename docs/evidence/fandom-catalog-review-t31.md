# T31 Fandom Pilot Cross-Catalog Review Evidence

> Date: 2026-09-07
> Mode: Lite / deterministic pre-review
> Review: `fandom-2025-pilot-cross-catalog-review-v1`

The review builder compared all 100 revision-frozen Wiki staging rows with the 120-row canonical
fixture and the 97-casting human-backed draft. It normalized brand and casting names with NFKD
ASCII conversion, case folding, and alphanumeric token spacing, then accepted exact keys only.
Fuzzy matching and identifier-only matching were disabled. An exact result is a casting-family
candidate for human review, not a variant mapping or promotion.

| Result | Rows | Distinct Wiki families |
|---|---:|---:|
| Exact human-backed casting family | `9` | `4` |
| Exact canonical fixture casting family | `0` | `0` |
| No exact family in either catalog | `91` | `49` |
| Total | `100` | `53` |

The four exact human-backed families are `'67 Chevy C10`, `Purple Passion`, `Subaru BRZ`, and
`Tesla Model S Plaid`. The report includes their human casting and provisional-variant IDs so a
reviewer can inspect the existing evidence. It does not copy those IDs into canonical fields.

Every row has `promotion_decision=hold_for_human_review`, `promotion_eligible=false`, and null
canonical UUID/ID. Recommended actions distinguish review of an existing human family from review
of a possible new casting family. The wording “possible” is deliberate: failure to find an exact
name is not proof that a casting is new.

The manifest freezes these inputs:

- Wiki staging SHA-256: `e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6`
- Canonical fixture SHA-256: `0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261`
- Human-backed catalog SHA-256: `d29b69cde8099cb229136a73b893ca99b6313d9652ead5ff4aea48c20242e74f`
- Review SHA-256: `720292870a04656df0a7a61ab7d649457990e09a19172b450f4557ad878f0c4e`

Five focused tests passed for row coverage, frozen counts, candidate boundaries, disabled unsafe
matching modes, input/output checksums, and deterministic regeneration. The complete host suite
passed 84/84. The `--check` command also rebuilt the result in memory and matched both checked-in
artifacts byte for byte. No network request, PostgreSQL write, runtime-catalog change, calibration,
or AI evaluation occurred in T31.

This artifact narrows the human workload but does not replace human verification. The next action
is to adjudicate the four matched family groups, followed by the 49 unmatched groups, while keeping
release/color decisions separate from casting identity.
