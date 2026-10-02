# Canonical Authority Review — T5-G2 Batch 4 progress

Date: 2026-10-02
Mode: Lite / Lean Industrial
Status: **BATCH 4 RECORDED — 12 APPROVED EXACT / 8 REVIEWED**

## Result and boundary

The three Nissan Skyline 2000GT-R LBWK entries at packet ordinals `4`, `13` and `20` moved from
`reviewed` to `approved_exact`. The approved scope is casting, release year, series, collector
number, series position and toy identifier as supported by the frozen community snapshot. Color and
edition stay null; `3rd Color` and `2nd Color` remain non-authoritative context.

| State / artifact | Count / status |
|---|---:|
| `approved_exact` candidates | 12 |
| Still `reviewed` | 8 |
| Still `staged` | 0 |
| T5-G1 + T5-G2 batch authorizations | 11 |
| T5-G1 + T5-G2 attestations | 32 |
| Public historical events | 32 |
| Frozen authority bundle / manifest | absent |
| RHB-T5 authorization | false |

Exactness is frozen-community-snapshot-relative, not manufacturer-certified truth. This document
does not reproduce or derive any private owner response.

## Integrity and replay

- Initial Batch 4 materialization returned `created`; two correctly scoped real checks returned
  `unchanged`.
- An initial operator replay supplied responses from different Gates and was rejected before any
  write. This confirms the exact-response equality guard fails closed.
- All 29 pre-existing events and 17 non-target candidate objects are preserved.
- Eleven authorization, 32 attestation and 20 latest-event links validate.
- Each new event has the exact six-field evidence set and expected Nissan Skyline values.
- The Batch 4 response differs from its T5-G1 response and all earlier T5-G2 responses.
- No approved-authority bundle or manifest was created.

## QA and privacy

Before materialization, focused verification reported `20 passed` and the full repository reported
`1359 passed, 1 warning`. Ruff, format, strict MyPy, compileall and diff checks passed. The warning
is the pre-existing Starlette/AnyIO deprecation.

After materialization, the focused suite again collected and passed 20 tests. Private/public
permissions are `0700` / `0600` / `0644`, the dedicated ignore rule covers private ledgers, and a
scan of 811 tracked/unignored text files found zero hits for all four real owner responses. The full
suite was not rerun after the state-only append.

## Artifact SHA-256

| Artifact | SHA-256 |
|---|---|
| Private T5-G2 batch authorization ledger | `50d9068eb15b36e9363896132708449c938cff7d976e25148902d1fc7a6e406b` |
| Private T5-G2 owner attestation ledger | `e17efea806ab7ee8ce09d251d87a30c6016a09a3c06329a8a4330cad068ef6f9` |
| Public authority candidates | `87d31c8e69fd8e3a6fe2fac1e0832dc64cad605c2b5834c246309664763b4104` |
| Public review events | `14ca957f1193cbacf7a6617f546160bbbab87e4adf8b5d2414e49846fbb92977` |

## Next Gate

T5-G2 remains incomplete. The next legal step is a separately implemented and tested bounded path
for the next frozen family batch, followed by a fresh owner decision. CAR-T5F, CAR-T6 and RHB-T5
remain outside the current authorization.
