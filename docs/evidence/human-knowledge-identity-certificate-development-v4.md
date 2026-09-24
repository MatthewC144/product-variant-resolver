# Human Knowledge identity-certificate set v4 — evidence

Date: 2026-09-24. Lite / Lean Industrial. Verdict: **valid historical experiment; no profile qualified**.

## Purpose and branch boundary

V4 tests whether corpus-wide minimal identity certificates can preserve legitimate shorthand while
rejecting corpus-absent or conflicting identities. One query support set is computed against all
public authority certificates before retrieved candidates are inspected. Candidates can only prove
membership in the one supported authority and must still pass conserved primary-frame conflicts.

Historical calibration runs before any proposed 16-positive/16-negative holdout. A non-reference
profile had to pass every exact 223/22/24 public gate before protocol/inventory freeze or new
retrieval. None did, so the experiment stopped on the historical-FAIL branch.

## Immutable evidence

| Artifact | SHA-256 / checksum |
|---|---|
| V4 development source | `cf2e207b97f395d2e4b334875ac17f2efa0500b1e675910e0242e562503b665a` |
| Certificate inventory checksum | `dafc709027af513e8bd6db20b80cc1c73e096461a05d13c69699b759f05edec7` |
| Historical calibration JSON | `d9ca782bd47252af0a1047776da3add97a5b40b2709b8a5d44bf4e6ecd78cf96` |
| Calibration manifest | `3bb89724f50f5a1229bf36023b84551fe7ee3cd27f5355f74d4fee1fd582ec95` |
| Calibration Markdown | `621ba4e10981790f1acda13d79aab2374a2a40ba2383a1a499e3ea6c65c5b4fb` |
| Preserved HIC-v1 source | `167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f` |
| Preserved HIE-v2 source | `c91d8e253f1cd19cf59b626e794673defe2e28aea6c993cbce350d1698e83a5e` |
| Preserved HICG-v3 source | `998f5af0983517d5ead54cf5fddaf46a57056245f92ac6d0c00c3279260ab173` |

The manifest binds 25 public input/source paths and records exact 223/22/24 denominators, zero
retrieval calls, zero eligible non-reference profiles, `private_local_artifacts_read: false`, and
`protocol_authorized: false`.

## Inventory and historical results

The committed corpus contains 142 documents grouped into 97 casting and 42 review-family authority
keys. Primary casting text produces 460 claims and 401 admissibly minimal certificates; 101 approved
aliases are bridges only. Seven shorter/contained authorities remain unresolved rather than using
series, color, release, or source metadata to manufacture uniqueness.

| Profile | Eligible | Existing positives | Required targets | Anchor positives | Anchor absent nonempty | HIC positives | HIC absent nonempty | R32/R33 vetoes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `reference-anchor` | no | 168/168 | 24/24 | 10/10 | 11/12 | 12/12 | 10/12 | 0/2 |
| `certificate-exact` | no | 42/168 | 6/24 | 0/10 | 0/12 | 3/12 | 0/12 | 2/2 |
| `certificate-structural` | no | 82/168 | 7/24 | 4/10 | 0/12 | 7/12 | 0/12 | 2/2 |
| `certificate-bounded` | no | 137/168 | 5/24 | 5/10 | 0/12 | 7/12 | 0/12 | 2/2 |

All profiles preserve 4/4 merge controls, produce zero forbidden existing candidates and zero
unrelated output, and have zero retrieval, certificate-construction, query-support, alias-alignment,
frame-comparison, and decision errors. The reference is comparison-only and unsafe. All three
certificate profiles are safe on measured negatives but miss required positive gates. The frozen
ordering therefore has no eligible input and returns `winner: null`.

## Reproducibility and QA

The branch command was executed once after pre-freeze QA:

```bash
PYTHONPATH=src .venv/bin/pvr-develop-human-knowledge-identity-certificate \
  --root . --freeze-protocol
```

It returned `calibration_failed_created`, `protocol_created: false`, and
`retrieval_executed: false`. Measured regressions bind every profile count plus the report and
manifest hashes. Sixty focused tests, 181 related regressions, and all 924 repository tests pass.
Targeted Ruff format/check, target-local strict MyPy with imports skipped, compileall, installed CLI,
artifact shape/hash checks, and `git diff --check` pass. The only suite warning is the existing
Starlette/AnyIO deprecation warning. Repository-wide strict MyPy still reports 51 known existing
errors in 18 files; the target-local v4 check has no diagnostic and this closure does not reformat or
rewrite unrelated modules.

## Release boundary

Exactly three v4 calibration files exist. There is no protocol, frozen inventory artifact, holdout
declaration, 16+16 pack, raw retrieval, selection, private evaluation, runtime import, API change,
Dual RAG integration, PostgreSQL change, canonical identity, release promotion, variant UUID,
color, wheel, tampo, edition, or packaging claim. This is reproducible negative evidence and an
example of a safety gate preventing unsupported promotion; it is not a deployable profile.
