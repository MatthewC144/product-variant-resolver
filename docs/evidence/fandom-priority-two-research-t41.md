# T41 Evidence — Priority-2 Family Research Batch 04

## Outcome

T41 verifies the checksum-frozen T40 cumulative queue and selects its first ten still-pending
priority-2 families. The batch covers 23 Wiki release rows. Eight exact names resolve to a dedicated
casting lineage and have confirmation from at least one publisher outside Fandom, producing machine
`create_new_casting` recommendations. Two grouped display names remain held because they identify
multiple same-scale tools.

| Casting family | Release rows | Machine recommendation |
|---|---:|---|
| Lamborghini Huracán Sterrato | `3` | `create_new_casting` |
| Max Steel | `2` | `create_new_casting` |
| Mazda Autozam | `3` | `create_new_casting` |
| Mazda MX-5 Miata | `2` | `hold` |
| Mazda REPU | `1` | `create_new_casting` |
| Mercedes-Benz 500 E | `2` | `create_new_casting` |
| Monster High Ghoul Mobile | `2` | `create_new_casting` |
| Morgan Super 3 | `3` | `create_new_casting` |
| Nerve Hammer | `2` | `create_new_casting` |
| Nissan Skyline 2000GT-R LBWK | `3` | `hold` |

All ten reviewer confirmations remain pending. Every release variant remains held and promotion
eligibility is zero.

## Identity findings

The 2025 `Mazda MX-5 Miata` page represents the separate HYW18 Chimera tool, while another 1:64
page uses the same display name for tool 2920 produced from 1991–2003. The queued name alone cannot
preserve that distinction, so the family remains held.

The HYW79/HYY30/HYX54 rows map to the dedicated `Nissan Skyline 2000GT-R LBWK (Tooned)` page and an
independent HYX54 record confirms that tool. A separate non-Tooned 1:64 tool, HCW32, uses the same
display name. The source toy numbers explain which release page is involved, but the grouped
name-only family identity is still not unique; this family also remains held.

Two nearby cases do not trigger holds. Nerve Hammer's original and two retools are documented as a
continuous lineage on one dedicated page. The Mercedes-Benz 500 E Hot Wheels XL page is explicitly
suffix-qualified and represents a 1:43 upscaled product, while the queued records and primary page
are 1:64. Both distinctions remain visible in the evidence.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| T40 cumulative queue input | `edee360faccb43b4bea58a91d5be67b511d9e41ea6a76f21ec4648bae83190b9` |
| Batch-04 source notes | `06616c879b3d8fa5d293338669b9497a29703a8055d44fce45c115e82efd6761` |
| Batch-04 research JSON | `07ae79197f81f3595b5323a38834fbfd776fd7043180bd3f6961c3a03d2c9673` |
| Batch-04 readable report | `cb9ae7e45b670d64ae6c2d4831a13eee4d6a70d5f9edf3aa16a032f8a98415c4` |
| Batch-04 manifest | `930f6bd72361501e93a792dae493d8b762325fe8df5a11625cd57f08b7a38923` |

The manifest binds the upstream queue, its manifest, the source notes, research JSON, and readable
report. The shared builder retains batch 01 as its default and supports explicit batches 02–04.

## Verification

Six focused tests verify the cumulative queue slice, 10-family / 23-row / 8-create / 2-hold counts,
the two conflicting same-name tool pages and their tool numbers, two-host evidence for every
creation recommendation, scale-qualified Mercedes context, continuous Nerve Hammer retool lineage,
pending reviewer status, variant hold, zero promotion, frozen hashes, and deterministic output.
All four research-batch `--check` commands reproduce their checked-in artifacts byte for byte.

The complete host-suite and supporting data/build/configuration results are recorded in the QA
review and Project Log after final verification.

## Remaining boundary

These are source-backed machine recommendations, not project-owner labels. Remote sources can
change, and text identity does not verify color or physical release details. T42 must present the
exact eight-create/two-hold packet to the project owner and record any authorization in a separate
decision file. The two holds require a tool-qualified name or explicit lineage key before safe
family creation.
