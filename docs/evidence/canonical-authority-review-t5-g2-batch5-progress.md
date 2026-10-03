# Canonical Authority Review — T5-G2 Batch 5 progress

Date: 2026-10-03
Mode: Lite / Lean Industrial
Status: **BATCH 5 RECORDED — 15 APPROVED EXACT / 5 REVIEWED**

## Result and boundary

The three `'21 Ford Bronco` entries at packet ordinals `5`, `7` and `17` moved from `reviewed` to
`approved_exact`. The approved scope is casting, release year, series, collector number, series
position and toy identifier as supported by the frozen community snapshot. Color and edition stay
null; `2nd Color` and `3rd Color` remain non-authoritative context.

| State / artifact | Count / status |
|---|---:|
| `approved_exact` candidates | 15 |
| Still `reviewed` | 5 |
| Still `staged` | 0 |
| T5-G1 + T5-G2 batch authorizations | 12 |
| T5-G1 + T5-G2 attestations | 35 |
| Public historical events | 35 |
| Frozen authority bundle / manifest | absent |
| RHB-T5 authorization | false |

Exactness is frozen-community-snapshot-relative, not manufacturer-certified truth. This document
does not reproduce or derive any private owner response.

## Integrity and replay

- Initial Batch 5 materialization returned `created`; two real checks returned `unchanged`.
- All 32 pre-existing events and 17 non-target candidate objects are preserved.
- Twelve authorization, 35 attestation and 20 latest-event links validate.
- Each new event has the exact six-field evidence set and expected `'21 Ford Bronco` values.
- The Batch 5 response differs from its T5-G1 response and all earlier T5-G2 responses.
- No approved-authority bundle or manifest was created.

The public event file is canonically ordered rather than append-ordered. An initial verification
compared the first 32 array positions and therefore reported a false mismatch without writing any
data. Rechecking by stable `event_id` map proved every prior event object is byte-for-byte equal.

## QA and privacy

Before materialization, focused verification reported `22 passed` and the full repository reported
`1361 passed, 1 warning`. Focused Ruff, format, strict MyPy, compileall and diff checks passed. The
warning is the pre-existing Starlette/AnyIO deprecation.

After materialization, the focused suite again reported `22 passed`. Private/public permissions are
`0700` / `0600` / `0644`, the dedicated ignore rule covers private ledgers, and a scan of 815
tracked/unignored text files found zero hits across all 12 private Gate responses, including the
Markdown-delimiter-stripped form of the new response. The full suite was not rerun after the
state-only append.

## Artifact SHA-256

| Artifact | SHA-256 |
|---|---|
| Private T5-G2 batch authorization ledger | `ad2ca0e2dded187a0b949629bcd2463c3c86c3b39ba4110300d25be02c7bcea9` |
| Private T5-G2 owner attestation ledger | `007a38d7f54c5b554acea528385f3497200fd4f42099bd421966596e445de699` |
| Public authority candidates | `4c69381dfebb519a592f62e775b4c3d139377a3e9c9a8403108c6037a1488682` |
| Public review events | `1a98bdbc2be56621a7b2c0ce7d8375b7c29918d8bca3bb60bf70c383ea67f4b1` |

## Next Gate

T5-G2 remains incomplete. The next legal step is a separately implemented and tested bounded path
for Batch 6, followed by a fresh owner decision. CAR-T5F, CAR-T6 and RHB-T5 remain outside the
current authorization.
