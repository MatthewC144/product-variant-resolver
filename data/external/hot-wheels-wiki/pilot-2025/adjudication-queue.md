# Fandom 2025 Pilot — Human Adjudication Queue

> This is a review worksheet, not a promotion file. All decisions are pending, and no
> family is eligible for canonical or PostgreSQL ingestion.

## Queue summary

| Item | Count |
|---|---:|
| Source rows | `100` |
| Distinct casting families | `53` |
| Priority 1: exact existing-family candidate | `4` |
| Priority 2: possible new family, research required | `49` |
| Completed decisions | `0` |
| Promotion-eligible families | `0` |

Allowed reviewer decisions are `merge_existing_family`, `create_new_casting`, `hold`,
and `reject`. A real decision must record reviewer, timestamp, reason, and supporting
evidence. Suggested actions below are machine pre-review only.

## Priority 1 — exact existing-family candidates

| Family | Wiki rows | Existing candidate | Suggested action | Decision |
|---|---:|---|---|---|
| '67 Chevy C10 | 2 | human-hot-wheels-67-chevy-c10 | merge_existing_family_candidate | pending |
| Purple Passion | 2 | human-hot-wheels-purple-passion | merge_existing_family_candidate | pending |
| Subaru BRZ | 3 | human-hot-wheels-subaru-brz | merge_existing_family_candidate | pending |
| Tesla Model S Plaid | 2 | human-hot-wheels-tesla-model-s-plaid | merge_existing_family_candidate | pending |

## Priority 2 — possible new families requiring research

| Family | Wiki rows | Suggested action | Decision |
|---|---:|---|---|
| 1988 Jeep Wagoneer | 2 | research_possible_new_casting_family | pending |
| 2020 Ram 1500 Rebel | 2 | research_possible_new_casting_family | pending |
| '21 Ford Bronco | 3 | research_possible_new_casting_family | pending |
| '22 Ford Maverick Custom | 1 | research_possible_new_casting_family | pending |
| '55 Chevy | 2 | research_possible_new_casting_family | pending |
| '66 Buick Riviera | 2 | research_possible_new_casting_family | pending |
| '69 Corvette Racer | 1 | research_possible_new_casting_family | pending |
| '80 El Camino | 1 | research_possible_new_casting_family | pending |
| '87 Audi quattro | 2 | research_possible_new_casting_family | pending |
| '90 Honda Civic EF | 3 | research_possible_new_casting_family | pending |
| '94 Audi Avant RS2 | 2 | research_possible_new_casting_family | pending |
| Alpha Pursuit | 2 | research_possible_new_casting_family | pending |
| Batman and Robin Batmobile | 2 | research_possible_new_casting_family | pending |
| Bogzilla | 1 | research_possible_new_casting_family | pending |
| Crescendo | 2 | research_possible_new_casting_family | pending |
| Custom '53 Chevy | 2 | research_possible_new_casting_family | pending |
| Custom Cadillac Fleetwood | 2 | research_possible_new_casting_family | pending |
| Deora III | 2 | research_possible_new_casting_family | pending |
| DMC DeLorean | 2 | research_possible_new_casting_family | pending |
| Donut Drifter | 1 | research_possible_new_casting_family | pending |
| Draftnator | 3 | research_possible_new_casting_family | pending |
| Fiat 500e | 1 | research_possible_new_casting_family | pending |
| Fish'd & Chip'd | 1 | research_possible_new_casting_family | pending |
| Ford Mustang GTD | 2 | research_possible_new_casting_family | pending |
| Ford Performance SuperVan 4 | 1 | research_possible_new_casting_family | pending |
| Haulerback | 2 | research_possible_new_casting_family | pending |
| Hirohata Merc | 2 | research_possible_new_casting_family | pending |
| Kei Swap | 2 | research_possible_new_casting_family | pending |
| Kick Kart | 2 | research_possible_new_casting_family | pending |
| Kowloon'd Hypervan | 2 | research_possible_new_casting_family | pending |
| Lamborghini Huracán Sterrato | 3 | research_possible_new_casting_family | pending |
| Max Steel | 2 | research_possible_new_casting_family | pending |
| Mazda Autozam | 3 | research_possible_new_casting_family | pending |
| Mazda MX-5 Miata | 2 | research_possible_new_casting_family | pending |
| Mazda REPU | 1 | research_possible_new_casting_family | pending |
| Mercedes-Benz 500 E | 2 | research_possible_new_casting_family | pending |
| Monster High Ghoul Mobile | 2 | research_possible_new_casting_family | pending |
| Morgan Super 3 | 3 | research_possible_new_casting_family | pending |
| Nerve Hammer | 2 | research_possible_new_casting_family | pending |
| Nissan Skyline 2000GT-R LBWK | 3 | research_possible_new_casting_family | pending |
| Nissan Skyline GT-R (BNR32) | 1 | research_possible_new_casting_family | pending |
| Power Wheels Dune Racer | 1 | research_possible_new_casting_family | pending |
| Proton Saga | 1 | research_possible_new_casting_family | pending |
| Small Bloc | 3 | research_possible_new_casting_family | pending |
| Standard Kart | 1 | research_possible_new_casting_family | pending |
| Super Twin Mill | 2 | research_possible_new_casting_family | pending |
| The Vanster | 2 | research_possible_new_casting_family | pending |
| Twin Mill Gen-E | 1 | research_possible_new_casting_family | pending |
| X-34 Landspeeder | 1 | research_possible_new_casting_family | pending |

## Review boundary

A family-level merge does not establish a release variant. Color, series, edition,
rarity, and toy-number identity must be reviewed separately. Do not ingest this queue
directly; only a later validated promotion artifact may write canonical records.
