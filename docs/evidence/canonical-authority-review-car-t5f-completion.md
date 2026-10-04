# Canonical Authority Review — CAR-T5F completion

Date: 2026-10-04
Mode: Lite / Lean Industrial
Status: **COMPLETE — ELIGIBLE FOR A FRESH RHB-T4 RE-AUDIT**

## Data result

The separately authorized CAR-T5F operation froze the validated two-Gate event chain into a safe
public authority bundle and manifest.

| Result | Value |
|---|---:|
| Bundle records | 20 |
| Distinct canonical UUIDs | 20 |
| `approved_exact` records | 20 |
| Qualifying families | 7 |
| Exact variant shortfall | 0 |
| Qualifying family shortfall | 0 |
| Gate result | `eligible_for_rhb_t4_reaudit` |
| Parent artifacts | 11 |
| Resolver output consulted / network requests | false / 0 |
| CAR-T6 / RHB-T5 authorized | false / false |

Exactness is limited to the six fields supported by the frozen community snapshot. Color and
edition remain null. This is not Mattel/manufacturer-certified truth and is not an RHB-T4 PASS.

## Installed artifacts and SHA-256

| Artifact | Visibility | Raw-file SHA-256 |
|---|---|---|
| CAR-T5F owner authorization | private, Git-ignored, `0600` | `5c7c86625bd310755bd4f9223eba8f1170a6cd68cd349c80508c38c3a88f3979` |
| `approved-authority.json` | tracked-safe, `0644` | `9922ff037fd79c61677008951a5de2fc2bfca52441c7f4d5b70d50c174dfa5ae` |
| `authority-manifest.json` | tracked-safe, `0644` | `a02a200207de229c88978eaf2469db485bc29f63a89a2fbd788d6c63b4a03467` |

The manifest binds the private authorization only through its irreversible authorization hash. The
public artifacts do not reproduce owner verbatim or private identity.

## Determinism and integrity

- Initial materialization returned `created`.
- Two real check-mode replays returned `unchanged`.
- Every record binds one candidate, catalog UUID, catalog-record hash, latest event and six distinct
  evidence hashes.
- All UUIDs and family/release identities are distinct for counting purposes.
- Manifest bundle hash, status counts, family composition, shortfalls and 11 parent digests were
  recomputed and validated.
- Private directory/authorization and public output permissions are `0700` / `0600` / `0644`.
- The private authorization path is confirmed by `git check-ignore`.

## Verification

Post-materialization affected suites passed:

- CAR-T5F freeze: 7 tests;
- CAR-T5P preparation: 23 tests;
- T5-G1 decisions: 71 tests;
- T5-G2 exact decisions: 26 tests;
- source-decision binding: 41 tests.

These 168 tests specifically cover the checked-in bundle boundary and the historical pre-freeze
fixtures. The final post-materialization full repository regression passed `1372 tests` with one
pre-existing Starlette/AnyIO deprecation warning in 13 minutes 48 seconds. Ruff/format, source-task
hash binding and `git diff --check` passed. A privacy scan across 830 tracked/unignored files found
zero hits for 25 private-response variants, including the CAR-T5F authorization and its unescaped
rendering variant.

## Next Gate

Only CAR-T6 may follow: a separate, freshly authorized and versioned RHB-T4 re-audit. It must
independently validate this bundle and may still fail closed. CAR-T5F does not authorize CAR-T6 or
RHB-T5, create benchmark queries/labels, or measure resolver/RAG/embedding quality.
