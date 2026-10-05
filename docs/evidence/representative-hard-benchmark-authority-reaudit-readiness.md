# Representative Hard Benchmark — CAR-T6 / RHB-T4 re-audit readiness

Date: 2026-10-04
Mode: Lite / Lean Industrial
Status: **READY FOR SEPARATE CAR-T6 OWNER AUTHORIZATION — NO RE-AUDIT MATERIALIZED**

## Result

The readiness path independently revalidated the CAR-T5F frozen authority bundle and reconstructed
a possible versioned RHB-T4 authority artifact in memory. It did not create a CAR-T6 authorization,
authority file or re-audit manifest.

| Check | Result |
|---|---:|
| CAR-T5F approved exact variants | 20 |
| Distinct canonical UUIDs | 20 |
| Qualifying multi-release families | 7 |
| Exact variant shortfall | 0 |
| Qualifying family shortfall | 0 |
| Historical RHB-T4 result | `blocked_insufficient_exact_authority` |
| Proposed versioned re-audit result | `passed_exact_authority_gate` |
| Historical checkpoint preserved | true |
| New authorization / authority / manifest | absent / absent / absent |
| Resolver output / labels consulted | false / false |
| Network requests | 0 |
| RHB-T5 authorized | false |

The readiness SHA-256 is
`0dedb97734cb0b93f5876bfd1b131a6aa9175783168613688eb3d0911fc123b9`.

## What changed and why

The original RHB-T4 audit is valid historical evidence: at that point the project had no approved
exact authority, so it correctly recorded a blocked result. Overwriting those files after CAR-T5F
would erase the audit trail. The new adapter therefore treats the old files as immutable inputs and
reserves separate `canonical-authority-reaudit-v1.json` and
`canonical-authority-reaudit-manifest-v1.json` outputs for a later authorized run.

Before proposing a PASS, the adapter replays CAR-T5F check mode and validates its private
authorization, public bundle and manifest; the 140-row catalog-v2; all latest exact events; six
supported field bindings per record; null color and edition; 20 unique UUIDs; and the seven-family
composition. The historical audit must still contain zero records and the exact original blocked
Gate values.

The CLI separates read-only `--readiness` from the state-changing path. Materialization requires
the exact fresh response twice and explicit CAR-T6, versioned RHB-T4 re-audit, and negative RHB-T5 /
query-pack / label boundaries. The verbatim response is designed to remain only in the Git-ignored
private workspace. The future three-file install is atomic and rolls back partial writes.

## Verification

- Focused CAR-T6 readiness/materialization suite: `6 passed`.
- CAR-T6 + historical RHB-T4 + CAR-T5F + source-binding regression: `61 passed`.
- Full repository regression: `1378 passed, 1 warning`; the warning is the pre-existing
  Starlette/AnyIO deprecation.
- Historical RHB-T4 builder checked twice: `unchanged`, `unchanged`.
- Real repository readiness: 20 exact variants, seven qualifying families and zero shortfalls;
  proposed new Gate `passed_exact_authority_gate`.
- Ruff and strict MyPy pass for the module, CLI and tests.
- Generic continuation, response mismatch, stale catalog and injected second-write failure all stop
  without leaving partial CAR-T6 outputs.
- Isolated authorized materialization returns `created`, `unchanged`, `unchanged`; public files do
  not contain the private owner response and the historical output bytes remain unchanged.

## Remaining Gate

CAR-T6 has not been executed in the real repository. A separate, exact owner authorization is still
required before the versioned authority and manifest may be written. Even if that re-audit passes,
RHB-T5 remains a later independent owner Gate; no query pack or labels may be created from this
readiness result.
