# Canonical Authority Review — T5-G2 Batch 2 readiness

Date: 2026-10-02
Mode: Lite / Lean Industrial
Status: **READY FOR OWNER GATE — NO BATCH 2 DECISION MATERIALIZED**

## Review scope

The next frozen family batch is Draftnator:

| Ordinal | Toy identifier | Casting | Release year | Series | Collector / position | Color | Edition |
|---:|---|---|---:|---|---|---|---|
| 2 | `HYW70` | Draftnator | 2025 | X-Raycers | `014` / `2/10` | null | null |
| 11 | `HYX67` | Draftnator | 2025 | X-Raycers | `014` / `2/10` | null | null |
| 18 | `HYY31` | Draftnator | 2025 | X-Raycers | `014` / `2/10` | null | null |

Batch SHA-256: `11adcabde3fd8594a8bca8e3a50c0e6b757ed87f714d5c3dd74e3534dad03d39`.

All six supported evidence rows agree for every entry. Source text describing second or third color
is context only: it does not identify a color value, is not promoted into the six-field exact scope,
and leaves both color and edition null. Any later approval is exact only relative to the frozen
community snapshot, not manufacturer-certified truth.

## Recorder behavior

The implementation now accepts the bounded prefix `[1, 2]` only. A Batch 2 append requires:

- the complete, valid T5-G1 seven-batch state;
- an existing and immutable T5-G2 Batch 1 authorization, three attestations and three events;
- a fresh Batch 2 response whose hash differs from the matching T5-G1 response;
- exact frozen candidate IDs, entry hashes, packet/catalog bindings and six evidence rows;
- atomic replacement of both private ledgers and both public state files.

Replay of Batch 1 after Batch 2 preserves the later prefix rather than rebuilding an older state.
Skipping Batch 1, requesting Batch 3, changing a prior object, reusing a cross-Gate response or
interrupting publication fails without a partial state.

## Verification

- T5-G2 focused tests: `16 passed`.
- Full repository: `1355 passed, 1 warning`.
- Ruff, format, strict MyPy, compileall and diff check: PASS.
- Real Batch 1 replay under the extended recorder: `unchanged`.
- Tracked/unignored privacy scan: 798 text files, zero real owner-response hits.
- Synthetic Batch 2 result: 6 approved exact / 14 reviewed, 2 T5-G2 authorizations, 6 T5-G2
  attestations and 26 total public events, with all prior Batch 1 objects preserved.

The warning is the pre-existing Starlette/AnyIO deprecation. Synthetic results are test evidence,
not real owner decisions.

## Current real state and stop condition

The real state remains 3 approved exact / 17 reviewed / 0 staged. The private exact-authorization
ledger contains only Batch 1. No authority bundle/manifest exists, and CAR-T5F, CAR-T6 and RHB-T5
remain unauthorized.

Execution stops at the Batch 2 Owner Gate. Materialization requires a new explicit outcome covering
all three listed toy identifiers, the snapshot-relative six-field scope, null color/edition and the
exclusion of later Gates.
