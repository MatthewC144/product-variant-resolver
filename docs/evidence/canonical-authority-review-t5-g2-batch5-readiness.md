# Canonical Authority Review — T5-G2 Batch 5 readiness

Date: 2026-10-02
Mode: Lite / Lean Industrial
Status: **READY FOR OWNER GATE — NO BATCH 5 DECISION MATERIALIZED**

## Review scope

The next frozen family batch is `'21 Ford Bronco`:

| Ordinal | Toy identifier | Casting | Release year | Series | Collector / position | Color | Edition |
|---:|---|---|---:|---|---|---|---|
| 5 | `HYY32` | `'21 Ford Bronco` | 2025 | HW Hot Trucks | `020` / `1/10` | null | null |
| 7 | `HYW73` | `'21 Ford Bronco` | 2025 | HW Hot Trucks | `020` / `1/10` | null | null |
| 17 | `HYX50` | `'21 Ford Bronco` | 2025 | HW Hot Trucks | `020` / `1/10` | null | null |

Batch SHA-256: `3e4b1006ac90c9555a2aaea031c0dc704ed2f71a6b97dac5a87712f9b55090a4`.

All six supported evidence rows agree. `2nd Color` and `3rd Color` wording is context only and does
not establish an actual color; color and edition therefore remain null. Any future approval is
exact only relative to the frozen community snapshot, not manufacturer-certified truth.

## Recorder behavior

The implementation accepts the bounded prefix `[1, 2, 3, 4, 5]` only. Batch 5 requires the
complete valid Batches 1–4 prefix, exact frozen family/identifier/entry bindings and a fresh response
distinct from the matching T5-G1 response and all earlier T5-G2 responses. Replay of earlier
batches retains later history. Missing Batch 4, requesting unsupported Batch 6, changing prior
objects or leaking owner text fails closed.

## Verification

- T5-G2 focused tests: `22 passed`.
- Full repository: `1361 passed, 1 warning`.
- Focused Ruff, format, strict MyPy, compileall and diff check: PASS.
- Real Batch 4 replay under the extended recorder: `unchanged`.
- Privacy scan: 813 tracked/unignored text files, zero hits for all four real owner responses.
- Synthetic Batch 5 result: 15 approved exact / 5 reviewed, 5 T5-G2 authorizations, 15 T5-G2
  attestations and 35 total events, with the complete Batches 1–4 prefix preserved.

The warning is the pre-existing Starlette/AnyIO deprecation. A non-gating exploratory repo-wide
Ruff scan also reported 245 pre-existing issues across older scripts, migrations and tests; the
three files in the Batch 5 change set pass the configured checks and the unrelated debt was not
mass-edited in this bounded task. Synthetic results are test evidence, not real owner decisions.

## Current state and stop condition

The real state remains 12 approved exact / 8 reviewed / 0 staged. The exact private ledger contains
only Batches 1–4. No authority bundle/manifest exists, and CAR-T5F, CAR-T6 and RHB-T5 remain
unauthorized.

Execution stops at the Batch 5 Owner Gate. Materialization requires a new explicit outcome covering
all three identifiers, the six-field scope, null color/edition and the exclusion of later Gates.
