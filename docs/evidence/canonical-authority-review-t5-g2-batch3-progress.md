# Canonical Authority Review — T5-G2 Batch 3 progress

Date: 2026-10-02
Mode: Lite / Lean Industrial
Status: **BATCH 3 RECORDED — 9 APPROVED EXACT / 11 REVIEWED**

## Result and boundary

The three Subaru BRZ entries at packet ordinals `3`, `8` and `14` moved from `reviewed` to
`approved_exact`. The approved scope is casting, release year, series, collector number, series
position and toy identifier as supported by the frozen community snapshot. Color and edition stay
null; `3rd Color` and `2nd Color - Zamac` remain non-authoritative context.

| State / artifact | Count / status |
|---|---:|
| `approved_exact` candidates | 9 |
| Still `reviewed` | 11 |
| Still `staged` | 0 |
| T5-G1 + T5-G2 batch authorizations | 10 |
| T5-G1 + T5-G2 attestations | 29 |
| Public historical events | 29 |
| Frozen authority bundle / manifest | absent |
| RHB-T5 authorization | false |

Exactness is frozen-community-snapshot-relative, not manufacturer-certified truth. This document
does not reproduce or derive any private owner response.

## Integrity and replay

- Initial Batch 3 materialization returned `created`; two real checks returned `unchanged`.
- All 26 pre-existing events and 17 non-target candidate objects are preserved.
- Ten authorization, 29 attestation and 20 latest-event links validate.
- Each new event has the exact six-field evidence set and expected Subaru BRZ values.
- The Batch 3 response differs from its T5-G1 response and both earlier T5-G2 responses.
- No approved-authority bundle or manifest was created.

## QA and privacy

Before materialization, focused verification reported `18 passed` and the full repository reported
`1357 passed, 1 warning`. Ruff, format, strict MyPy, compileall and diff checks passed. The warning
is the pre-existing Starlette/AnyIO deprecation.

After materialization, the focused suite again reported `18 passed`. Private/public permissions are
`0700` / `0600` / `0644`, the dedicated ignore rule covers private ledgers, and a scan of 804
tracked/unignored text files found zero hits for all three real owner responses. The full suite was
not rerun after the state-only append.

## Artifact SHA-256

| Artifact | SHA-256 |
|---|---|
| Private T5-G2 batch authorization ledger | `ff3a2ecf55f1624e6953eb17f5133af060790755bc705ea4bd24c58c60143de9` |
| Private T5-G2 owner attestation ledger | `e2bd2dcc828fbe023aa0de70d9a80c0cb1bf07ab2d0a4117e18485b5cc93d7b2` |
| Public authority candidates | `4353c5a61f9800f046ff2cce2132b8c2562ce9baebb3f9c8d69550e76e294db6` |
| Public review events | `45a7e03d97ba508f0474eec14cf6dbcab80c22238a64ce474693787cef3b3a65` |

## Next Gate

T5-G2 remains incomplete. The next legal step is a separately implemented and tested bounded path
for the next frozen family batch, followed by a fresh owner decision. CAR-T5F, CAR-T6 and RHB-T5
remain outside the current authorization.
