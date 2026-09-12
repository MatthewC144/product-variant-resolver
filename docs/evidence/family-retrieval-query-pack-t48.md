# Family Retrieval Query Pack — T48.2 Evidence

> Mode: Lite / Lean Industrial
>
> Status: PASS for output-blind authoring and pre-score freeze
>
> Date: 2026-09-12
>
> Subsequent state: the project owner confirmed this unchanged checksum for T48.3

## Frozen artifact and boundary

The official `family-retrieval-query-pack-v1` contains 105 test-only cases and is frozen at SHA-256
`26e244c04325f7909fb222b6cdd32ee2301253db17f0b8b97cf2f63ac4358733`. Its manifest binds the query
bytes, 142-document input versions/checksums, normalization and retrieval source checksums,
`human-knowledge-hybrid-v2`, `hashing-v1` with 192 dimensions, RRF `k=60`, and Top-5 evaluation.

No Human Knowledge retrieval, API request, candidate generation, rank, score, expected label,
benchmark construction, live marketplace request, or Wiki request occurred while authoring or
freezing this pack. The query cases contain only the allowlisted authorship, grouping, query,
challenge, and identity-reference fields. `retriever_output_viewed=false` is present in all 105.

## Positive-family questions for project-owner review

The family name is the identity question used to author the pair; it is not a retrieval result.

| Family | Marketplace-noise query | Lexical-variation query |
|---|---|---|
| 1988 Jeep Wagoneer | 2025 Hot Wheels 1988 Jeep Wagoneer red sealed card | HW 88 jeep wagoner loose truck |
| 2020 Ram 1500 Rebel | 2025 Hot Wheels 2020 Ram 1500 Rebel pickup sealed | ram fifteen hundred rebl truck |
| '21 Ford Bronco | Hot Wheels '21 Ford Bronco blue mainline unopened | 2021 frd bronco off road toy |
| '22 Ford Maverick Custom | Hot Wheels '22 Ford Maverick Custom red carded truck | ford mavrick custom 2022 pickup |
| '66 Buick Riviera | Hot Wheels '66 Buick Riviera teal mint blister | sixty six buick riv custom |
| '69 Corvette Racer | Hot Wheels '69 Corvette Racer yellow blister pack | 69 corvett race car loose |
| '80 El Camino | Hot Wheels '80 El Camino black 2025 carded pickup | eighties elcamino ute loose |
| '87 Audi quattro | 2025 '87 Audi quattro blue Hot Wheels mainline sealed | 87 audi quatro rally car loose |
| '90 Honda Civic EF | Hot Wheels '90 Honda Civic EF white carded import | ninety honda civic ef hatch |
| '94 Audi Avant RS2 | Hot Wheels '94 Audi Avant RS2 silver mint on card | 94 audi avnt rs 2 wagon diecast |
| Alpha Pursuit | Alpha Pursuit police car blue sealed Hot Wheels | alfa pursuit patrol vehicle |
| Bogzilla | Bogzilla green monster fantasy car unopened blister | bogzila creature vehicle |
| Crescendo | Crescendo red music themed car sealed on card | crescndo fantasy model |
| Custom '53 Chevy | Custom '53 Chevy red Hot Wheels loose seller lot | custm 53 chevy pickup model |
| Custom Cadillac Fleetwood | Custom Cadillac Fleetwood gold loose Hot Wheels auction | custom caddy fleetwd lowrider |
| Deora III | Deora III purple Hot Wheels new on short card | deora 3 surf truck |
| DMC DeLorean | DMC DeLorean silver time machine car sealed card | d m c deloran movie car |
| Donut Drifter | Donut Drifter pink bakery car sealed collector item | donut drift pastry racer |
| Draftnator | Draftnator black fantasy racer mint on card | draftn8r race car |
| Fiat 500e | Fiat 500e yellow electric city car sealed blister | fiat five hundred e mini ev |
| Fish'd & Chip'd | Fish'd & Chip'd green Hot Wheels sealed seller listing | fish n chipped novelty car loose |
| Ford Mustang GTD | Ford Mustang GTD grey 2025 sealed collector car | ford mustng g t d supercar |
| Ford Performance SuperVan 4 | Ford Performance SuperVan 4 white carded race van | ford perf super van four electric racer |
| Haulerback | Haulerback purple short card mint collector listing | haulerbak truck model |
| Hirohata Merc | Hirohata Merc teal carded custom car collector sale | hirohata mercury custom loose |
| Kei Swap | Kei Swap red Japanese mini truck sealed listing | kei swp custom microvan |
| Kick Kart | Kick Kart yellow Hot Wheels new in package | kik kart fantasy racer |
| Kowloon'd Hypervan | Kowloon'd Hypervan red carded Hong Kong van | kowloon hyper van street model |
| Lamborghini Huracán Sterrato | Lamborghini Huracán Sterrato orange unopened collector car | lambo huracan sterato off road model |
| Max Steel | Max Steel blue loose fantasy car seller lot | max steal racer on short card |
| Mazda Autozam | Mazda Autozam blue kei car sealed blister listing | mazda auto zam tiny coupe |
| Mazda REPU | Mazda REPU orange pickup Hot Wheels carded sale | mazda r e p u rotary truck |
| Mercedes-Benz 500 E | Mercedes-Benz 500 E black premium style diecast lot | mercedes benz five hundred e sedan |
| Monster High Ghoul Mobile | Monster High Ghoul Mobile pink carded fantasy vehicle | monsterhi ghoulmobile toy car |
| Morgan Super 3 | Morgan Super 3 red three wheeler sealed listing | morgan super three roadster |
| Nerve Hammer | Nerve Hammer orange Hot Wheels blister pack listing | nerv hammer fantasy car |
| Proton Saga | Proton Saga white Hot Wheels 2025 mint card | protn saga malaysia sedan |
| Small Bloc | Small Bloc blue Hot Wheels short card seller lot | small block fantasy coupe |
| Super Twin Mill | Super Twin Mill chrome Hot Wheels new in blister | supertwin mill fantasy racer |
| The Vanster | The Vanster green Hot Wheels unopened van listing | vanstr custom van toy |
| Twin Mill Gen-E | Twin Mill Gen-E silver carded electric concept car | twinmill gen e ev model |
| X-34 Landspeeder | X-34 Landspeeder tan Star Wars Hot Wheels carded | x34 land speeder sci fi vehicle |

The four one-token identities intentionally lose their exact token: `Bogzilla → bogzila`,
`Crescendo → crescndo`, `Draftnator → draftn8r`, and `Haulerback → haulerbak`. They remain in the
test even though the current shared-token eligibility rule may fail; that is a precommitted risk,
not a reason to simplify the questions.

## Governance-control questions

| Control | Frozen query | Intended question |
|---|---|---|
| Merge: Purple Passion | Purple Passion hot rod dark blue sealed toy | Should reuse the existing human-backed casting, never create a duplicate review family |
| Merge: Tesla Model S Plaid | Tesla Plaid Model S red Hot Wheels loose | Should reuse the existing human-backed casting, never create a duplicate review family |
| Merge: '67 Chevy C10 | 67 C10 Chevy pickup orange collector lot | Should reuse the existing human-backed casting, never create a duplicate review family |
| Merge: Subaru BRZ | Subaru BRZ blue carded import diecast | Should reuse the existing human-backed casting, never create a duplicate review family |
| Hold: '55 Chevy | 55 Chevy orange loose mystery casting | Ambiguous lineage must remain unmaterialized |
| Hold: Nissan Skyline GT-R (BNR32) | BNR 32 Nissan Skyline GTR red collector car | Ambiguous tool lineage must remain unmaterialized |
| Hold: Nissan Skyline 2000GT-R LBWK | LBWK Nissan Skyline 2000 GTR blue short card | Ambiguous tool lineage must remain unmaterialized |
| Hold: Power Wheels Dune Racer | Power Wheels Dune Racer orange diecast listing | Renamed relationship must remain unmaterialized |
| Hold: Standard Kart | Mario Standard Kart loose Hot Wheels vehicle | Multi-tool identity must remain unmaterialized |
| Hold: Batman and Robin Batmobile | Batman Robin Batmobile black red carded car | Ambiguous identity must remain unmaterialized |
| Hold: Mazda MX-5 Miata | Mazda Miata MX5 roadster 2025 diecast | Ambiguous tool lineage must remain unmaterialized |

The ten unrelated controls are `juxaprenoid`, `klyzomareth`, `nexuvandrix`, `phyrqotulon`,
`plaxumdrith`, `qevornyxal`, `trazuphelix`, `vortiqsable`, `wexorinblath`, and `zxqvornelith`.
Automated validation proves each normalized token has no overlap with the full Human Knowledge
search vocabulary.

## Static QA and next gate

The authoring source reproduces `query-pack.json` byte for byte. The contract independently confirms
105 total cases, exact 84/4/7/10 class counts, exact style counts, 42 two-style groups, four
single-token challenges, unique sorted IDs and normalized queries, allowlisted fields/tags, no
prohibited normalized equality, broken lexical phrases, complete control coverage, test-only use,
and all exclusions. The query-pack manifest also reproduces byte for byte without mutation.

The focused suite now contains eight passing tests, including two checks against the actual frozen
pack. The complete repository suite passes 192/192 in 2.250 seconds on the final tree; Python
compilation, the configured 100-character code-line check, and `git diff --check` also pass. Ruff is
not installed on this host, so no Ruff result is claimed. The only suite message is the previously
known, non-failing Starlette legacy-`httpx` environment warning.

This is authoring evidence, not retrieval-quality evidence. T48.3 may begin only after the project
owner confirms the frozen query/reference pairs; its decision file must bind the exact hash above.
Any query edit invalidates this review and requires a new pre-score freeze.
