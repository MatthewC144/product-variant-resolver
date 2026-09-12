# Family-Level Human Knowledge T47 — Implementation Evidence

> Mode: Lite / Lean Industrial
>
> Current milestone: T47.1–T47.3 complete; T47.4 pending
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

### T47.2 typed runtime result

T47.2 loads the projection and manifest at service construction and rejects any schema, version,
checksum, filename, source, count, field, eligibility, exclusion, identity, ordering, alias, or
source-record invariant outside the frozen v1 contract. It combines two internal dataclass types
behind common `knowledge_type`, `knowledge_id`, `knowledge_uuid`, and `searchable_text` properties:

| Runtime property | Verified result |
|---|---:|
| Provisional-variant documents | `100` |
| Review-family documents | `42` |
| Combined documents | `142` |
| Unique knowledge IDs / UUIDs | `142 / 142` |
| Exact family queries recovered within Top-5 | `42 / 42` |
| Worst expected-family rank | `2` |
| BMW M3 GT2 expected type/rank | `provisional_variant / 1` |
| Proton Saga canonical result | `no_match / null identity` |

Both types share the existing sparse, 192-dimensional `hashing-v1` dense, and RRF ranking pool.
Health now reports `review-family-knowledge-fandom-2025-r790665-v1` and
`human-knowledge-hybrid-v2`. The human retrieval trace records bounded total, variant, and family
candidate counts without storing the raw title. Missing and checksum-invalid projection inputs
produce HTTP 503 and no canonical identity.

The frozen canonical evaluation remains 21 test cases, Recall@25 `1.0`, Top-1 `1.0`, hard-negative
accuracy `1.0`, precision `1.0`, false-match rate `0.0`, and coverage `0.8333`. Thirty-five focused
configuration/loader/retrieval/service/API/observability tests passed in 0.635 seconds; the complete
host suite passed **182/182** in 1.712 seconds. Python compilation, deterministic projection and
registry checks, fixture validation, Docker Compose configuration, and whitespace checks passed.
The two existing UI harness tests also passed after their fixture version moved to v2. The host has
neither MyPy nor Ruff installed, so no result from either tool is claimed. The known
machine-wide Starlette legacy-`httpx` TestClient warning remains non-failing.

### T47.3 discriminated API/UI result

T47.3 replaces the temporary variant-only serializer with a Pydantic discriminated union. OpenAPI
publishes `knowledge_type` as the discriminator and maps it to exactly two strict branches:
`provisional_variant` and `review_family`. Variant responses contain their casting and provisional-
variant IDs, reviewed labels, examples, and case provenance; family responses instead contain the
review-family ID/UUID, approved aliases, and source-record provenance. Type-inapplicable identity
fields are absent, not copied, overloaded, or filled with null placeholders.

The service applies `debug_candidate_limit` once to the combined RRF order and converts every item
within that slice according to its document type. The debug payload also includes
`review-family-knowledge-fandom-2025-r790665-v1`, while requests without debug still omit the entire
debug object and therefore omit human candidates and versions. A one-result Proton Saga request
returns the expected family candidate but retains `status=no_match` and null canonical identity; a
one-result BMW M3 GT2 request retains the existing provisional-variant shape.

The browser table now includes a visible Type column. Review-family rows show approved aliases and
the explicit text `family only — variants unreviewed`; provisional variants preserve the existing
series/variant display. The UI continues to create elements and assign `textContent` only. The Node
harness injects markup-shaped strings into both candidate types and verifies the strings remain
literal text with no script-side effect.

Seventeen focused API/UI tests passed in 0.277 seconds. They cover the OpenAPI discriminator, both
serialized branches and field absence, a shared result limit, family projection version, default
debug omission, canonical isolation, safe UI states, and inert markup-shaped values. The complete
host suite passes **184/184**. The known environment-wide Starlette legacy-`httpx` warning remains
non-failing and is unrelated to this change.

### Remaining boundary

T47.1 satisfies the projection portions of FHK-R1–R4, FHK-R13, and FHK-R16. T47.2 satisfies the
runtime portions of FHK-R5–R11 and FHK-R13–R16. T47.3 satisfies the public contract and UI portions
of FHK-R5, FHK-R11–R12, and FHK-R14. All remain subject to T47.4's final cross-requirement Lite QA,
deterministic data-chain rerun, frozen evaluation comparison, and documentation closure.

Exact-name retrieval remains only the T47 specification's wiring simulation. No independent
quality result, production claim, calibration change, PostgreSQL integration, or 3,000-row scale
claim is introduced by these completed milestones.
