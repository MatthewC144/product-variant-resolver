# Representative Hard Benchmark — CAR-T6 / versioned RHB-T4 re-audit

Date: 2026-10-04
Mode: Lite / Lean Industrial
Status: **COMPLETE — PASSED EXACT-AUTHORITY GATE; RHB-T5 UNAUTHORIZED**

## Audit result

The separately authorized CAR-T6 operation fed the frozen CAR-T5F bundle into a new, versioned
RHB-T4 re-audit. The new result passes the exact-authority threshold while preserving the earlier
honest blocked audit as immutable history.

| Result | Value |
|---|---:|
| Approved exact authority records | 20 |
| Distinct canonical UUIDs | 20 |
| Qualifying multi-release families | 7 |
| Exact variant shortfall | 0 |
| Qualifying family shortfall | 0 |
| New Gate result | `passed_exact_authority_gate` |
| Historical Gate result | `blocked_insufficient_exact_authority` |
| Historical checkpoint preserved | true |
| Resolver output / benchmark labels consulted | false / false |
| Network requests | 0 |
| RHB-T5 authorized | false |

The exactness claim remains limited to casting, release year, series, collector number, series
position and toy identifier as supported by the frozen community snapshot. Color and edition remain
null. This is not Mattel/manufacturer-certified truth.

## Installed artifacts and SHA-256

| Artifact | Visibility | Raw-file SHA-256 |
|---|---|---|
| CAR-T6 owner authorization | private, Git-ignored, `0600` | `f0ceebd4ab012b744e6ce374c5af76a6780ff72e2e318cc1eeff43834c8ebf24` |
| `canonical-authority-reaudit-v1.json` | tracked-safe, `0644` | `72c11aeb8db03267a8deca4f50eb09d89c2c423a7e9ca983f498f76e80553117` |
| `canonical-authority-reaudit-manifest-v1.json` | tracked-safe, `0644` | `dfb71d8fa5f6964f7a29983c569974a549633022bb12e18f9046fb0e680a6862` |

The private authorization's semantic checksum is
`bfd7c0a9aae2df86a28d875700714fd9c89a1c000f0dc41eab8684c8a80c6fe6`.
The public manifest binds this checksum without reproducing the verbatim owner response.

## Historical integrity and determinism

- Initial materialization returned `created`; two real check-mode replays returned `unchanged`.
- The historical authority and manifest retain raw SHA-256 values
  `f0a9fe00f8f48cd81eb603170847f6485db6940c8c6e421bbb601789446ce1af` and
  `10c38740b94f43d5ebba4932d0c946bcd2997eac59f0e52ba71c0d4bc5b44f7d`.
- The old RHB-T4 builder also returned `unchanged` twice after CAR-T6 materialization.
- The new manifest records the historical zero-record blocked result and
  `preserved_without_overwrite=true`.
- The public artifacts contain no verbatim owner response. The private path is covered by the
  dedicated Git ignore rule.
- No resolver output, benchmark label, network request, query pack or label artifact participated in
  the audit.

## Verification

- Post-materialization CAR-T6, historical RHB-T4 and CAR-T5F focused regression: `21 passed`,
  including direct verification of the checked-in public authority and manifest.
- Full repository regression: `1379 passed, 1 warning`; the warning is the pre-existing
  Starlette/AnyIO deprecation.
- After replacing the test authorization with an explicit `TEST-ONLY` response, the CAR-T6 and
  source-binding suites were rerun on the final tree: `48 passed`.
- Two real CAR-T6 check replays: `unchanged`, `unchanged`.
- Two post-materialization historical RHB-T4 checks: `unchanged`, `unchanged`.
- Artifact modes: private authorization `0600`; public authority and manifest `0644`.
- The authority contains 20 unique `approved_exact` UUIDs and the manifest independently records
  seven qualifying families and zero shortfalls.

## Next Gate

The versioned RHB-T4 authority Gate has passed. The next benchmark construction task, RHB-T5,
remains prohibited until a new, separate owner authorization is recorded. CAR-T6 does not authorize
query-pack authoring, label authoring, resolver execution or benchmark-quality claims.
