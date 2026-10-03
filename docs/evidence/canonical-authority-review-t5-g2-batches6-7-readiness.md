# Canonical Authority Review — T5-G2 Batches 6–7 readiness

Date: 2026-10-03
Mode: Lite / Lean Industrial
Status: **READY FOR TWO SEQUENTIAL OWNER GATES — NO BATCH 6/7 DECISIONS MATERIALIZED**

## Review scope

Batch 6 is Morgan Super 3:

| Ordinal | Toy identifier | Release year | Series | Collector / position | Color | Edition |
|---:|---|---:|---|---|---|---|
| 6 | `HYX48` | 2025 | Factory Fresh | `015` / `1/5` | null | null |
| 12 | `HYW13` | 2025 | Factory Fresh | `015` / `1/5` | null | null |
| 19 | `HYY33` | 2025 | Factory Fresh | `015` / `1/5` | null | null |

Batch 6 SHA-256: `61600ebabe813de0368ffb7c2ef847dfb7eeccbfbc7301c90a9aa3464fcf76e6`.

Batch 7 is Mazda MX-5 Miata:

| Ordinal | Toy identifier | Release year | Series | Collector / position | Color | Edition |
|---:|---|---:|---|---|---|---|
| 9 | `HYW18` | 2025 | HW Dream Garage | `001` / `2/5` | null | null |
| 15 | `HYX57` | 2025 | HW Dream Garage | `001` / `2/5` | null | null |

Batch 7 SHA-256: `9b2606df8eb2c1b4a05cd7b415717300eeaf34ae112f92f62d0defcdd2b1e3e1`.

Every entry has the same six supported fields used by earlier batches: casting, release year,
series, collector number, series position and toy identifier. Neither batch has color/edition
evidence or variant context to promote, so both fields remain null. Any future approval is exact
only relative to the frozen community snapshot, not manufacturer-certified truth.

## Recorder behavior and sequencing

The implementation accepts the bounded prefix `[1, 2, 3, 4, 5, 6, 7]` only.

- Batch 6 requires complete, immutable Batches 1–5 and a new Batch 6 response.
- Batch 7 requires complete, immutable Batches 1–6 and a different new Batch 7 response.
- Missing predecessors, requesting Batch 8, stale family/identifier/entry bindings, owner-text
  leakage or attempts to reuse one response across Gates fail closed.
- Replaying any supported earlier batch retains all later history.

The two readiness paths were implemented together for efficiency, but their decisions remain
sequential and separately hash-bound. Batch 7 cannot be written before Batch 6 validates.

## Verification

- T5-G2 focused tests: `26 passed`.
- Full repository: `1365 passed, 1 warning`.
- Focused Ruff, format, strict MyPy, compileall and diff check: PASS.
- Real Batch 5 replay under the extended recorder: `unchanged`.
- Privacy scan: 817 tracked/unignored text files, zero hits across all 12 private Gate responses and
  the stripped Markdown variant.
- Synthetic Batch 6 result: 18 approved exact / 2 reviewed, 6 T5-G2 authorizations, 18 T5-G2
  attestations and 38 total events, with Batches 1–5 preserved.
- Synthetic Batch 7 result: 20 approved exact / 0 reviewed, 7 T5-G2 authorizations, 20 T5-G2
  attestations and 40 total events, with Batches 1–6 preserved.

The warning is the pre-existing Starlette/AnyIO deprecation. Synthetic results are test evidence,
not real owner decisions.

## Current state and stop condition

The real state remains 15 approved exact / 5 reviewed / 0 staged. The exact private ledger contains
only Batches 1–5. No authority bundle/manifest exists, and CAR-T5F, CAR-T6 and RHB-T5 remain
unauthorized.

Execution stops at the two Owner Gates. The next allowed action is a Batch 6 decision covering its
three identifiers and six-field/null boundary. Only after Batch 6 validates may a separately worded
Batch 7 decision cover its two identifiers. A single reused response is not accepted.
