# Canonical Authority Review — T5-G2 Batch 3 readiness

Date: 2026-10-02
Mode: Lite / Lean Industrial
Status: **READY FOR OWNER GATE — NO BATCH 3 DECISION MATERIALIZED**

## Review scope

The next frozen family batch is Subaru BRZ:

| Ordinal | Toy identifier | Casting | Release year | Series | Collector / position | Color | Edition |
|---:|---|---|---:|---|---|---|---|
| 3 | `JBB55` | Subaru BRZ | 2025 | HW J-Imports | `048` / `3/5` | null | null |
| 8 | `HYY12` | Subaru BRZ | 2025 | HW J-Imports | `048` / `3/5` | null | null |
| 14 | `HYW99` | Subaru BRZ | 2025 | HW J-Imports | `048` / `3/5` | null | null |

Batch SHA-256: `8b68298be1e9ca8b7e801e6a0604ed379bf374c168395c4dd536a5e71c5f2066`.

All six supported evidence rows agree. `3rd Color` and `2nd Color - Zamac` source wording remains
context only: it does not establish an actual color and does not make Zamac an edition. Color and
edition therefore remain null. Any future approval is exact only relative to the frozen community
snapshot, not manufacturer-certified truth.

## Recorder behavior

The implementation accepts the bounded prefix `[1, 2, 3]` only. Batch 3 requires the complete valid
Batches 1–2 prefix, exact frozen family/identifier/entry bindings and a fresh response distinct from
the corresponding T5-G1 response. Replay of any earlier supported batch retains later history.
Missing Batch 2, requesting unsupported Batch 4, changing prior objects or leaking owner text fails
closed.

## Verification

- T5-G2 focused tests: `18 passed`.
- Full repository: `1357 passed, 1 warning`.
- Ruff, format, strict MyPy, compileall and diff check: PASS.
- Real Batch 2 replay under the extended recorder: `unchanged`.
- Privacy scan: 802 tracked/unignored text files, zero hits for both real owner responses.
- Synthetic Batch 3 result: 9 approved exact / 11 reviewed, 3 T5-G2 authorizations, 9 T5-G2
  attestations and 29 total events, with the complete Batches 1–2 prefix preserved.

The warning is the pre-existing Starlette/AnyIO deprecation. Synthetic results are test evidence,
not real owner decisions.

## Current state and stop condition

The real state remains 6 approved exact / 14 reviewed / 0 staged. The exact private ledger contains
only Batches 1–2. No authority bundle/manifest exists, and CAR-T5F, CAR-T6 and RHB-T5 remain
unauthorized.

Execution stops at the Batch 3 Owner Gate. Materialization requires a new explicit outcome covering
all three identifiers, the six-field scope, null color/edition and the exclusion of later Gates.
