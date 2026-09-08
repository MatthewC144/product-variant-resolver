# T34 Priority-1 Family Decision Evidence

> Date: 2026-09-08
> Mode: Lite / attributable family decision application
> Result: `fandom-2025-pilot-adjudicated-queue-v1`

After receiving the explicit proposal that four exact-name casting families be merged while all
nine release variants remain held, the project owner requested execution of the next step. T34
records that follow-up authorization in a separate decision batch rather than altering the
machine-generated pending queue.

| State | Count |
|---|---:|
| Completed family decisions | `4` |
| Accepted exact-target family merges | `4` |
| Pending family decisions | `49` |
| Wiki release variants held | `9` |
| Promotion-eligible families | `0` |
| Canonical/PostgreSQL rows created | `0` |

The four targets are `human-hot-wheels-67-chevy-c10`,
`human-hot-wheels-purple-passion`, `human-hot-wheels-subaru-brz`, and
`human-hot-wheels-tesla-model-s-plaid`. Each decision records `project_owner`, UTC timestamp
`2026-09-08T14:06:18Z`, a family-specific reason, evidence references, and the explicit
`casting_family_only` / variant-`hold` boundary.

The applier validates the queue and evidence checksums, decision schema, batch identity,
provenance, UTC timestamp, unique known family IDs, allowed outcome, written reason, non-empty
evidence, exact candidate target, family-only scope, and variant hold. A test that substitutes an
unrelated target fails closed. The original all-pending queue is not modified; the accepted state
is a separately frozen derived artifact.

The decision-file SHA-256 is
`ef17632c486850ab8f39604462e474c8c0e97894a8a8fc0003aef58b5fab03f0`; the adjudicated-result
SHA-256 is `6ab11ddef990e31918e507372c451cc0bfce531d7c9ec41e91ecc680288d0082`;
the readable-result SHA-256 is
`bd916df6b82866f87766c5ab038646d6aee90c4dd69e93a57120aef91cbaf023`.

Five focused tests passed for state counts, attribution, family/variant scope, exact-target
enforcement, fail-closed invalid input, hashes, and deterministic regeneration. The complete host
suite passed 99/99. T30–T33 checks, fixture validation, Python compilation, both Compose
configurations, and patch whitespace checks also passed.

T34 confirms only that the Wiki rows and existing human draft belong to the same four named casting
families. It does not assert canonical identity or validate any individual year, color, series,
edition, rarity, collector number, or toy number. The next data-expansion work is evidence research
for the 49 priority-2 possible-new families.
