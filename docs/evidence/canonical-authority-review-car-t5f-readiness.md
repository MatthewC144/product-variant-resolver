# Canonical Authority Review — CAR-T5F readiness

Date: 2026-10-04
Mode: Lite / Lean Industrial
Status: **READY FOR SEPARATE OWNER AUTHORIZATION — NO BUNDLE MATERIALIZED**

## Result

The new CAR-T5F readiness path revalidated the complete two-Gate exact-authority state and
recomputed the bundle composition without writing a freeze authorization or public bundle.

| Check | Result |
|---|---:|
| Approved exact candidates | 20 |
| Reviewed / staged candidates | 0 / 0 |
| Public review events | 40 |
| T5-G1 + T5-G2 batch authorizations | 14 |
| Candidate families | 7 |
| Qualifying families with at least two releases | 7 |
| Exact variant shortfall | 0 |
| Qualifying family shortfall | 0 |
| Proposed Gate result | `eligible_for_rhb_t4_reaudit` |
| Freeze authorization / bundle / manifest | absent / absent / absent |
| CAR-T6 / RHB-T5 authorized | false / false |

The readiness report SHA-256 is
`eb690e4a501b3026bf534963dcc347550be3691c4f05826fe142ea8592ca9cbf`.

## Implementation boundary

`canonical_authority_freeze.py` adds a deterministic builder that reconstructs each prospective
bundle record from the frozen packet, terminal candidate state and latest T5-G2 event. It verifies
the catalog UUID and record hash, six distinct field-evidence hashes, family/release identity,
source-decision binding and latest-event link before counting a record.

The CLI has two distinct modes:

- `--readiness` is read-only and cannot accept authorization arguments;
- freeze/check mode requires the exact fresh owner response twice, a CAR-T5F and authority-bundle
  scope, plus explicit boundaries keeping CAR-T6 and RHB-T5 unauthorized.

When later authorized, the verbatim response will be written only to the ignored private workspace.
The tracked bundle and manifest contain only safe IDs, hashes, counts, composition and public role
metadata. The three-file install is atomic and restores or removes partial files after failure.

## Verification

- New CAR-T5F focused suite: `7 passed`.
- Complete authority regression: `303 passed`.
- Full repository regression: `1372 passed, 1 warning` in 13 minutes 34 seconds; the warning is the
  pre-existing Starlette/AnyIO deprecation.
- Ruff and strict MyPy: passed for the new module and CLI.
- Compileall and `git diff --check`: passed.
- Privacy scan: zero hits for 17 private-response variants across 826 tracked/unignored files.
- Real repository readiness: 20 exact variants, seven qualifying families, zero shortfalls.
- Generic `繼續下一步`: rejected before any freeze artifact is created.
- Mismatched owner response, stale candidate state and injected second-write failure: rejected or
  rolled back with no partial output.
- Materialization/replay in an isolated test repository: `created`, `unchanged`, `unchanged`.

After the final output-permission/readiness-state hardening, the seven focused tests were rerun and
passed again. The full regression result therefore precedes only that bounded hardening, whose
affected behavior is covered by the post-change focused rerun.

## Owner Gate

The next state-changing operation is still CAR-T5F itself. It requires a separate owner response;
this readiness result is not that authorization. CAR-T6 and RHB-T5 remain later independent Gates.
