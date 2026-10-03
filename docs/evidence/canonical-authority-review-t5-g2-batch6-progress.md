# Canonical Authority Review — T5-G2 Batch 6 progress

Date: 2026-10-03
Mode: Lite / Lean Industrial
Status: **BATCH 6 RECORDED — 18 APPROVED EXACT / 2 REVIEWED**

## Result and boundary

The three Morgan Super 3 entries at packet ordinals `6`, `12` and `19` moved from `reviewed` to
`approved_exact`. The approved scope is casting, release year, series, collector number, series
position and toy identifier as supported by the frozen community snapshot. Color and edition stay
null, and no variant context was promoted.

| State / artifact | Count / status |
|---|---:|
| `approved_exact` candidates | 18 |
| Still `reviewed` | 2 |
| Still `staged` | 0 |
| T5-G1 + T5-G2 batch authorizations | 13 |
| T5-G1 + T5-G2 attestations | 38 |
| Public historical events | 38 |
| Frozen authority bundle / manifest | absent |
| RHB-T5 authorization | false |

Exactness is frozen-community-snapshot-relative, not manufacturer-certified truth. This document
does not reproduce or derive any private owner response.

## Integrity and replay

- Initial Batch 6 materialization returned `created`; two real checks returned `unchanged`.
- All 35 pre-existing events and 17 non-target candidate objects are preserved by stable identity.
- Thirteen authorization, 38 attestation and 20 latest-event links validate.
- Each new event has the exact six-field evidence set and expected Morgan Super 3 values.
- The Batch 6 response differs from its T5-G1 response and all earlier T5-G2 responses.
- No Batch 7 event, approved-authority bundle or authority manifest was created.

## QA and privacy

Before materialization, focused verification reported `26 passed` and the full repository reported
`1365 passed, 1 warning`. Focused Ruff, format, strict MyPy, compileall and diff checks passed. The
warning is the pre-existing Starlette/AnyIO deprecation.

After materialization, the focused suite again reported `26 passed`. Private/public permissions are
`0700` / `0600` / `0644`, the dedicated ignore rule covers private ledgers, and a scan of 819
tracked/unignored text files found zero hits across 15 private-response variants. The full suite was
not rerun after the state-only append.

## Artifact SHA-256

| Artifact | SHA-256 |
|---|---|
| Private T5-G2 batch authorization ledger | `4a3d7b9756ba22ce466294830eb40d1e5f98c041397bb0c42fbbfb2dc794e25b` |
| Private T5-G2 owner attestation ledger | `b8d86a15b5d8edc85c7076aafadbb255362ec2fa8c09fa2a5ec217021ecafcd4` |
| Public authority candidates | `9c782389c59c9dee6c16a83105ec797f05dc0b47ed1d5a748de065a656198bad` |
| Public review events | `3f12562dcb96728c84ebff2fa8f8e0e65905a99e02f92209d025c8b7b7748bb1` |

## Next Gate

T5-G2 remains incomplete. Batch 7 readiness is already verified, but its two Mazda MX-5 Miata
entries require a different, fresh owner decision. CAR-T5F, CAR-T6 and RHB-T5 remain outside the
current authorization.
