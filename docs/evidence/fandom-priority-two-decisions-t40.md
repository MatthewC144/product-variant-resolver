# T40 Evidence — Priority-2 Batch-03 Owner Decisions

## Outcome and authorization boundary

After receiving the complete T39 outcome, exact ten-family list, and explicit explanation that the
next step would accept family recommendations while keeping variants held, the project owner asked
to execute that next step. T40 records this bounded authorization as ten `create_new_casting`
decisions under `project_owner` at `2026-09-08T19:42:28Z`.

The decision layer covers Draftnator, Fiat 500e, Fish'd & Chip'd, Ford Mustang GTD, Ford Performance
SuperVan 4, Haulerback, Hirohata Merc, Kei Swap, Kick Kart, and Kowloon'd Hypervan exactly once.
Every item references its frozen T39 packet and source evidence, uses `casting_family_only` scope,
has a written family-specific reason, keeps `target_family_id` null, and sets the release-variant
decision to `hold`.

## Cumulative state

The new queue is derived from the T38 checkpoint rather than modifying it. It retains all four
priority-1 decisions, all ten priority-2 batch-01 decisions, and all ten priority-2 batch-02
decisions before appending the ten current decisions. The resulting 53-family queue reports:

| State | Count |
|---|---:|
| Completed family decisions | `34` |
| Pending family decisions | `19` |
| Accepted existing-family merges | `4` |
| Accepted new-family decisions | `28` |
| Held family decisions | `2` |
| Release rows remaining variant-held under completed decisions | `64` |
| Promotion-eligible families | `0` |

These counts describe the adjudication layer. They are not an increase in the canonical catalog,
human-backed runtime catalog, or PostgreSQL tables.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| Owner decision file | `ecd3af4c0b003d3458e719109eff9b41c546787d3cd5c5bb5d313dd4d316dd8c` |
| Derived cumulative queue | `edee360faccb43b4bea58a91d5be67b511d9e41ea6a76f21ec4648bae83190b9` |
| Readable adjudication result | `523af3b17045ee2f3322fdad57d5666f9fbc0c634d957aad7c32e32bc41d7bde` |
| Derived manifest | `8adc3ba56d7b55e03958de335c2c8a82c351094636fd496d54cd430422b00704` |

The manifest also binds the T38 cumulative queue and manifest, the T39 research and manifest, and
the T40 decision file. Prior input artifacts remain unchanged.

## Validation and negative cases

The T40 focused suite verifies cumulative counts, all-ten recommendation agreement, attributable
family-only scope, eighteen current release rows held, preservation of each earlier decision batch,
four ordered history entries, output hashes, and deterministic regeneration. Negative tests change
one accepted creation to a hold, omit one family, and reuse the batch-02 ID; the applier rejects all
three instead of producing a partial or rewritten queue.

The shared decision applier supports batches 01, 02, and 03 while preserving byte-for-byte output
for both earlier batches. The complete host-suite and static build/configuration results are
recorded in the QA review and Project Log after final verification.

## Remaining boundary

Conversation provenance is attributable within the repository but is not a cryptographic
signature. The twenty-eight accepted new-family outcomes still have no stable review-catalog
entity IDs. No release row has verified color or canonical variant identity, and nothing from this
decision artifact is loaded by the Dual-RAG runtime or inserted into PostgreSQL. T41 may research
the next ten pending families; catalog materialization requires a separate design and tests.
