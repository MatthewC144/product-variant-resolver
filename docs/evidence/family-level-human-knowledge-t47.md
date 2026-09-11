# Family-Level Human Knowledge T47 — Implementation Evidence

> Mode: Lite / Lean Industrial
>
> Current milestone: T47.1 complete; T47.2–T47.4 pending
>
> Date: 2026-09-11

## Delivered boundary

T47.1 creates a separately authorized runtime projection from the immutable T46 audit registry. It
does not load the new data into the service. The generated artifact contains 42 `review_family`
documents and only the identity/name/provenance fields permitted by the design.

| Measured property | Result |
|---|---:|
| Review-family documents | `42` |
| Accepted source-record references | `79` |
| Skipped existing-family merges | `4` families / `9` rows |
| Skipped holds | `7` families / `12` rows |
| Accounted source release references | `100` |
| Provisional variant documents | `0` |
| Canonical promotions | `0` |
| PostgreSQL rows | `0` |

Future searchable fields are frozen as `brand`, `casting`, and `aliases`. `source_record_ids` are
retained only as debug provenance. Decision reasons, evidence URLs, held release objects, toy and
collector numbers, series, and variant notes are absent from every document.

## Reproducibility and negative behavior

`build_review_family_knowledge.py` first checks the T46 registry/manifest filenames, schemas,
versions, checksum, identity namespace, 42/4/7 family counts, 79/9/12 row split, 100 unique held
release references, and zero-promotion boundaries. It validates all 42 accepted identities and
writes the projection and manifest through temporary files only after all checks pass.

The manifest freezes both input checksums, the projection checksum, document fields, searchable
fields, usage exclusions, counts, and zero variant/canonical/PostgreSQL states. Its projection SHA-
256 is `8615cbb99b453673599e1f9baf54f6900314d7ba64e53a31ea7891c71810b9d7`.

Six focused tests passed in 0.150 seconds. They cover exact selection, allowlisted document shape,
input/output checksums, byte reproduction, non-mutating `--check`, and rejection of changed
checksums, wrong counts, unstable UUIDs, unreviewed alias additions, widened eligibility/exclusions,
and stale outputs. The negative command test begins with known-good output files and proves they
remain byte-identical after failure.

## Regression evidence

- The complete host suite passed **174/174** in 1.612 seconds.
- Python compilation passed for the new builder and tests.
- Projection `--check`, T46 registry `--check`, and the existing fixture validator passed.
- Source formatting contains no lines beyond the configured 100-character limit.
- Ruff was not installed in the host environment; compilation and the executable suite are the
  available local static/runtime evidence for this bounded task.
- The host suite emitted only the already documented non-failing Starlette legacy-`httpx`
  TestClient warning. This task changes no dependency or API code.

## Requirement coverage and remaining work

T47.1 satisfies the projection portions of FHK-R1–R4, FHK-R13, and FHK-R16. It does not claim the
runtime portions of readiness or complete QA. T47.2 must add strict loading, typed family/variant
documents, the unified 142-document hybrid index, readiness metadata, and canonical-isolation
regressions. T47.3 then exposes the discriminated debug API/UI, and T47.4 closes full Lite QA.

Exact-name retrieval remains only the T47 specification's wiring simulation. No independent
quality result, production claim, calibration change, PostgreSQL integration, or 3,000-row scale
claim is introduced by this milestone.
