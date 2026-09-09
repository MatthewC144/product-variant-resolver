# T42 Evidence — Priority-2 Batch-04 Owner Decisions

## Outcome and authorization boundary

After receiving the complete T41 result, the exact eight-create/two-hold split, the two held family
names, and the explanation that all release rows would remain held, the project owner requested
execution of the next step. T42 records that bounded authorization under `project_owner` at
`2026-09-09T13:52:51Z`.

Lamborghini Huracán Sterrato, Max Steel, Mazda Autozam, Mazda REPU, Mercedes-Benz 500 E, Monster
High Ghoul Mobile, Morgan Super 3, and Nerve Hammer are accepted as review-layer new-family
decisions. Mazda MX-5 Miata and Nissan Skyline 2000GT-R LBWK remain held because each display name
spans separate same-scale tools. Every item references its frozen T41 packet and source evidence,
uses `casting_family_only` scope, keeps `target_family_id` null, and holds its release variants.

## Cumulative state

The batch-04 queue is derived from the checksum-verified T40 checkpoint rather than modifying it.
It preserves all four priority-1 decisions and all thirty prior priority-2 decisions before
appending the ten current outcomes:

| State | Count |
|---|---:|
| Completed family decisions | `44` |
| Pending family decisions | `9` |
| Accepted existing-family merges | `4` |
| Accepted new-family decisions | `36` |
| Held family decisions | `4` |
| Release rows remaining variant-held under completed decisions | `87` |
| Promotion-eligible families | `0` |

These are adjudication-layer counts. They do not add rows to the canonical catalog,
`human_backed_catalog.json`, PostgreSQL, calibration data, evaluation labels, or either Dual-RAG
retrieval source.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| Owner decision file | `172775063922d1ab2ae999ddcea43a09826b02f4f01c97fbb1c3e0b9671c8dbf` |
| Derived cumulative queue | `123e7432bc68710e9f3c6c01393b07456ff018c54619ea2111825c27f2ff5847` |
| Readable adjudication result | `f83431ed2febf8607bb692a146142f0e874812bc9124e7ee1db1f16d9627eff3` |
| Derived manifest | `34c61547ea3ef76fd97fb46a54667272a99c2dce23f8c87568969d5df90136a9` |

The manifest also binds the T40 cumulative queue and manifest, the T41 research and manifest, and
the T42 decision file. Earlier inputs and checkpoints remain immutable.

## Validation and negative cases

The focused T42 module passes 6/6. It verifies cumulative counts, the exact eight creations and
two named holds, all twenty-three current release rows held, complete attribution, preservation of
four earlier decision groups, five ordered history entries, checksums, and deterministic rebuilds.
Negative tests change an approved outcome, omit one family, reuse a prior batch ID, and widen a
variant decision; the applier rejects every altered batch instead of producing a partial queue.

The shared applier reproduces all four priority-2 checkpoints byte for byte. The complete host suite
passes 147/147. Python compilation, data validators, both Compose configurations, and whitespace
checks are recorded in the final QA review and Project Log.

## Remaining boundary

Conversation provenance is attributable but is not a cryptographic signature. The thirty-six
accepted new-family decisions have no stable review-catalog IDs and are not searchable. The two
current holds still require tool-qualified identities. T43 may research the remaining nine pending
families; only a later, separately specified materialization step may write accepted entities into
the review catalog or PostgreSQL.
