# Canonical Authority Review — T5-G2 Batch 4 readiness

Date: 2026-10-02
Mode: Lite / Lean Industrial
Status: **READY FOR OWNER GATE — NO BATCH 4 DECISION MATERIALIZED**

## Review scope

The next frozen family batch is Nissan Skyline 2000GT-R LBWK:

| Ordinal | Toy identifier | Casting | Release year | Series | Collector / position | Color | Edition |
|---:|---|---|---:|---|---|---|---|
| 4 | `HYX54` | Nissan Skyline 2000GT-R LBWK | 2025 | HW J-Imports | `026` / `1/5` | null | null |
| 13 | `HYW79` | Nissan Skyline 2000GT-R LBWK | 2025 | HW J-Imports | `026` / `1/5` | null | null |
| 20 | `HYY30` | Nissan Skyline 2000GT-R LBWK | 2025 | HW J-Imports | `026` / `1/5` | null | null |

Batch SHA-256: `e99f5321da7911dcc8d87976a17ef909acaba2b78c4d4a1fb4c90d6279314c9c`.

All six supported evidence rows agree. `3rd Color` and `2nd Color` wording is context only and does
not establish an actual color; color and edition therefore remain null. Any future approval is
exact only relative to the frozen community snapshot, not manufacturer-certified truth.

## Recorder behavior

The implementation accepts the bounded prefix `[1, 2, 3, 4]` only. Batch 4 requires the complete
valid Batches 1–3 prefix, exact frozen family/identifier/entry bindings and a fresh response distinct
from the matching T5-G1 response. Replay of earlier batches retains later history. Missing Batch 3,
requesting unsupported Batch 5, changing prior objects or leaking owner text fails closed.

## Verification

- T5-G2 focused tests: `20 passed`.
- Full repository: `1359 passed, 1 warning`.
- Ruff, format, strict MyPy, compileall and diff check: PASS.
- Real Batch 3 replay under the extended recorder: `unchanged`.
- Privacy scan: 806 tracked/unignored text files, zero hits for all three real owner responses.
- Synthetic Batch 4 result: 12 approved exact / 8 reviewed, 4 T5-G2 authorizations, 12 T5-G2
  attestations and 32 total events, with the complete Batches 1–3 prefix preserved.

The warning is the pre-existing Starlette/AnyIO deprecation. Synthetic results are test evidence,
not real owner decisions.

## Current state and stop condition

The real state remains 9 approved exact / 11 reviewed / 0 staged. The exact private ledger contains
only Batches 1–3. No authority bundle/manifest exists, and CAR-T5F, CAR-T6 and RHB-T5 remain
unauthorized.

Execution stops at the Batch 4 Owner Gate. Materialization requires a new explicit outcome covering
all three identifiers, the six-field scope, null color/edition and the exclusion of later Gates.
