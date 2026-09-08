# T39 Evidence — Priority-2 Family Research Batch 03

## Outcome

T39 verifies the checksum-frozen T38 cumulative queue and selects its first ten still-pending
priority-2 families. The batch covers 18 Wiki release rows. Each queued name resolves to one
dedicated Hot Wheels Wiki casting page and has exact-name corroboration from at least one publisher
outside Fandom, so all ten receive machine `create_new_casting` recommendations. No recommendation
has been accepted by the project owner: reviewer confirmation remains pending, every release
variant remains held, and promotion eligibility is zero.

The researched families are Draftnator, Fiat 500e, Fish'd & Chip'd, Ford Mustang GTD, Ford
Performance SuperVan 4, Haulerback, Hirohata Merc, Kei Swap, Kick Kart, and Kowloon'd Hypervan.

## Identity boundary

The research distinguishes a uniquely named related tool from a same-name homonym. Fiat 500e has a
dedicated electric-model casting page separate from Fiat 500. The current Hirohata Merc page and an
independent automotive source describe a newer mainline tool while retaining the older, differently
named `'51 Merc` as lineage context. Those relations are stored in `related_casting_pages`, but do
not force a hold because each exact queued name still selects one dedicated tool. This does not
weaken the batch-02 rule: if separate tools share the same display name, the family remains held.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| T38 cumulative queue input | `81911e948fd00e76e6da7255ab1174c1697871ac59c3bf674dc5bae645fbc497` |
| Batch-03 source notes | `6f2753b7e736145970096660ba07ce4553ebd423b1f551c7780dc7b91274cf86` |
| Batch-03 research JSON | `1d38a7bbffbf905283d4c7be6a24495547df425723ef610539c1f3eee07c432d` |
| Batch-03 readable report | `44472564cac68bb3073c0ceeab2dbc663994cb859318a7cab5f5f0f5b3d4c940` |
| Batch-03 manifest | `92dae730213f9928dd5811d8a43657038a037bd85462653fc2639db44a33e97b` |

The manifest also binds the upstream queue, queue manifest, source notes, generated research JSON,
and readable report by checksum. The builder defaults to batch 01 for compatibility and explicitly
supports `--batch 2` and `--batch 3` for later cumulative checkpoints.

## Verification

The six T39 tests verify cumulative selection order, the 10-family / 18-row / 10-create counts,
two distinct source hosts for every recommendation, retention of the Fiat and Hirohata related-tool
distinctions, pending reviewer status, variant hold, zero promotion, frozen hashes, and byte-for-byte
regeneration. All three research-batch `--check` commands also pass, proving that adding batch 03 did
not change the earlier frozen outputs.

The complete host suite result and supporting compilation/configuration checks are recorded in the
QA review and Project Log after the final verification run.

## Limitations and next boundary

Remote web sources can change after the research date, and the repository stores concise
observations and URLs rather than archived copies of every page. The source check supports a
bounded family recommendation; it does not verify color, release-level identity, a canonical UUID,
or production completeness. T40 must present this exact frozen packet to the project owner and
record any authorized decisions in a separate attributable layer before the cumulative queue can
advance.
