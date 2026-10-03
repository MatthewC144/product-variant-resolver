# Canonical Authority Review — T5-G2 Batch 7 progress

Date: 2026-10-03
Mode: Lite / Lean Industrial
Status: **BATCH 7 AND T5-G2 RECORDED — 20 APPROVED EXACT / 0 REVIEWED**

## Result and boundary

The two Mazda MX-5 Miata entries at packet ordinals `9` and `15` moved from `reviewed` to
`approved_exact`. The approved scope is casting, release year, series, collector number, series
position and toy identifier as supported by the frozen community snapshot. Color and edition stay
null, and no variant context was promoted.

| State / artifact | Count / status |
|---|---:|
| `approved_exact` candidates | 20 |
| Still `reviewed` | 0 |
| Still `staged` | 0 |
| T5-G1 + T5-G2 batch authorizations | 14 |
| T5-G1 + T5-G2 attestations | 40 |
| Public historical events | 40 |
| Frozen authority bundle / manifest | absent |
| RHB-T5 authorization | false |

T5-G2 is complete across seven separately authorized family batches. Exactness remains relative to
the frozen community snapshot, not manufacturer-certified truth. This document does not reproduce
or derive any private owner response.

## Integrity and replay

- Initial Batch 7 materialization returned `created`; two real checks returned `unchanged`.
- All 38 pre-existing events and 18 non-target candidate objects are preserved by stable identity.
- Fourteen authorization, 40 attestation and 20 latest-event links validate.
- Each new event has the exact six-field evidence set and expected Mazda MX-5 Miata values.
- The Batch 7 response differs from its T5-G1 response and all earlier T5-G2 responses.
- No approved-authority bundle or manifest was created.

## QA and privacy

Before materialization, focused verification reported `26 passed` and the full repository reported
`1365 passed, 1 warning`. Focused Ruff, format, strict MyPy, compileall and diff checks passed. The
warning is the pre-existing Starlette/AnyIO deprecation.

After materialization, the focused suite again reported `26 passed`. Private/public permissions are
`0700` / `0600` / `0644`, the dedicated ignore rule covers private ledgers, and a scan of 821
tracked/unignored text files found zero hits across 17 private-response variants. The full suite was
not rerun after the state-only append.

## Artifact SHA-256

| Artifact | SHA-256 |
|---|---|
| Private T5-G2 batch authorization ledger | `18ec492bd1fa95d8e55ddcc2f4795dc847e75913a83d2dd8dca0db1a18de5d9d` |
| Private T5-G2 owner attestation ledger | `7c7fcfefd525b2697a38237bd69e8511b31ca7e16a01a61c93178b25fae97daf` |
| Public authority candidates | `e6de7352f99f53161a3d2a8957d4c8b34821cb7beec34f091ab15c39af4c7112` |
| Public review events | `6bc25e5057af6d7e583208678f56143b69a990a4ea0b00a0d7c5d4d54d9f4186` |

## Next Gate

No T5-G2 decision remains pending. The next legal step is a separate owner authorization for
CAR-T5F, which must validate every parent/link and freeze the safe authority bundle or publish exact
shortfalls. CAR-T6 and RHB-T5 remain separately unauthorized.
