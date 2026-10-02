# Canonical Authority Review — T5-G2 Batch 2 progress

Date: 2026-10-02
Mode: Lite / Lean Industrial
Status: **BATCH 2 RECORDED — 6 APPROVED EXACT / 14 REVIEWED**

## Result and boundary

The three Draftnator entries at packet ordinals `2`, `11` and `18` moved from `reviewed` to
`approved_exact`. The approved scope is limited to casting, release year, series, collector number,
series position and toy identifier as supported by the frozen community snapshot. Color and edition
remain null; second/third-color context is not promoted into an exact value.

| State / artifact | Count / status |
|---|---:|
| `approved_exact` candidates | 6 |
| Still `reviewed` | 14 |
| Still `staged` | 0 |
| T5-G1 + T5-G2 batch authorizations | 9 |
| T5-G1 + T5-G2 attestations | 26 |
| Public historical events | 26 |
| Frozen authority bundle / manifest | absent |
| RHB-T5 authorization | false |

Exactness is relative to the named frozen community revision and is not manufacturer-certified
truth. This document does not reproduce or derive either private owner response.

## Integrity and replay

- Initial Batch 2 materialization returned `created`.
- Two real Batch 2 checks returned `unchanged`.
- All 23 pre-existing events are object-equivalent after the append.
- All 17 non-target candidate objects are object-equivalent after the append.
- Nine authorization, 26 attestation and 20 candidate-latest-event links validate.
- Each of the three new events has exactly the six supported evidence fields and expected values.
- The Batch 2 response is fresh relative to both its T5-G1 response and the Batch 1 T5-G2 response.
- The approved-authority bundle and manifest remain absent.

## QA and privacy

Before materialization, focused verification reported `16 passed` and the full repository reported
`1355 passed, 1 warning`. Ruff, format, strict MyPy, compileall and diff checks passed. The warning
is the pre-existing Starlette/AnyIO deprecation.

After materialization, the focused suite again reported `16 passed`. Private/public permissions are
`0700` / `0600` / `0644`, the dedicated ignore rule covers the private ledgers, and a scan of 800
tracked/unignored text files found zero hits for either real owner response. The full suite was not
rerun after the state-only append.

## Artifact SHA-256

| Artifact | SHA-256 |
|---|---|
| Private T5-G2 batch authorization ledger | `a8c379f865f5df53137706bca668a7f6b5368655771b1fbdee6a8b0bdf180a00` |
| Private T5-G2 owner attestation ledger | `0a9e44dded19534dd58694f6cdf5cb3999656796e6799f649a7033af5774b319` |
| Public authority candidates | `cdd721ac63d6f0d472538fadfedc8c3cfe4b10b2dc29eca37613d6a3bc8de445` |
| Public review events | `a925bab95fb383319b90980a49f346e6e7c358d492dd5d0b2e583f6fb192c1ab` |

## Next Gate

T5-G2 remains incomplete. The next legal step is a separately implemented and tested bounded path
for the next frozen family batch, followed by a fresh owner decision. CAR-T5F, CAR-T6 and RHB-T5
remain outside the current authorization.
