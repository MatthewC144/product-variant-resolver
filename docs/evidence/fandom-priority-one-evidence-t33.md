# T33 Priority-1 Fandom Family Evidence

> Date: 2026-09-08
> Mode: Lite / reviewer evidence preparation
> Packet: `fandom-2025-priority-one-family-evidence-v1`

T33 joins the four priority-1 adjudication groups with the retained human-backed source evidence.
The packet covers all nine Wiki release rows and exactly four human casting targets. It preserves
human labels, initial source names when available, structured series/variant fields, failure
categories, source case IDs, provisional variant IDs, and the existing casting IDs/UUIDs.

| Family | Wiki rows | Wiki series | Human series/variant | Family recommendation | Variant recommendation |
|---|---:|---|---|---|---|
| `'67 Chevy C10` | `2` | HW Hot Trucks (2025) | HW Workshop / Green; initial text says 2015 | Merge existing family | Hold |
| `Purple Passion` | `2` | HW Designed By (2025) | mainline / Pink; human label says 2026 | Merge existing family | Hold |
| `Subaru BRZ` | `3` | HW J-Imports (2025) | Walmart Exclusive / Zamac | Merge existing family | Hold |
| `Tesla Model S Plaid` | `2` | HW EV (2025) | mainline / Red | Merge existing family | Hold |

Every family recommendation is based only on exact normalized brand and casting across two frozen
repository sources. The packet does not claim the release variants match. Subaru BRZ is the only
packet with a shared explicit Wiki/human variant token, `zamac`; it remains unverified because the
series labels differ and the Wiki staging color is null. The other packets have no shared explicit
variant token.

All reviewer confirmations remain pending, `variant_identity_verified` is false, and promotion
eligibility is zero. Accepting a recommendation later would connect the Wiki rows to an existing
human casting family only; it would not create a canonical UUID or approve year, color, series,
edition, rarity, collector number, or toy number identity.

The packet SHA-256 is
`4d6ede8ba1bbb3447f2d403885d4d68bb9d71893cbf012994b2be37e77ad8294`; the readable report
SHA-256 is `077d9b078514b8628b99244936f426652a46679f4e74642858c00c8067db98ab`.
The manifest also freezes the T32 queue, its manifest, and the human-backed catalog.

Five focused tests passed for four-packet/nine-row coverage, exact target linkage, retained human
evidence, family-versus-variant boundaries, the Subaru Zamac fact, pending confirmations, output
checksums, and deterministic regeneration. The complete host suite passed 94/94. T30, T31, and T32
checks; fixture validation; Python compilation; both Compose configurations; and patch whitespace
checks also passed.

T33 performs no new Wiki request, PostgreSQL write, canonical-catalog mutation, model evaluation,
or human confirmation. Its purpose is to make the user's next four decisions small, readable, and
evidence-backed without claiming that an AI recommendation is a human label.
