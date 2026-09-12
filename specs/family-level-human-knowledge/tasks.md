# Family-Level Human Knowledge — Tasks

> Mode: Lite / Lean Industrial
>
> Status: In progress; T47.1–T47.3 complete

## Task order

### T47.1 — Build the review-family runtime projection `[backend]`

- [x] Implement the deterministic projection builder and non-mutating `--check`. _(→FHK-R1–R4,FHK-R13,FHK-R16)_
- [x] Generate and freeze the 42-document projection and manifest. _(→FHK-R2–R4)_

Files:

- `scripts/build_review_family_knowledge.py`
- `data/review_family_knowledge.json`
- `data/review_family_knowledge_manifest.json`
- `tests/test_review_family_knowledge_projection.py`

Acceptance:

- Only T46 `new_families` become documents; 4 merges and 7 holds are accounted for but absent.
- Searchable fields are limited to brand/casting/approved aliases.
- Outputs reproduce byte for byte; invalid/stale/widened input cannot overwrite good output.

Completion evidence (2026-09-11): six focused projection tests pass; the generated manifest freezes
42 family documents, 79 accepted source records, 4/7 skipped merge/hold families, all 100 source
release references, and zero variant/canonical/PostgreSQL rows. The complete suite passes 174/174.

### T47.2 — Load typed documents into the combined v2 retriever `[backend]`

- [x] Add strict family-projection/manifest loading and typed document models. _(→FHK-R5,FHK-R13–R14)_
- [x] Generalize sparse/dense/RRF indexing to the shared 142-document pool. _(→FHK-R6–R10)_
- [x] Add settings, startup readiness, version metadata, and bounded type counts. _(→FHK-R11,FHK-R13–R15)_

Files:

- `src/product_variant_resolver/config.py`
- `src/product_variant_resolver/human_knowledge.py`
- `src/product_variant_resolver/service.py`
- `src/product_variant_resolver/api.py`
- `tests/unit/test_human_knowledge.py`
- `tests/unit/test_observability.py`
- `tests/integration/test_catalog_service.py`
- `tests/api/test_api.py`

Acceptance:

- Combined catalog contains exactly 100 provisional variants and 42 review families.
- All 42 exact family queries recover within Top-5; the reviewed BMW regression remains correct.
- Holds/merges create no family documents and human candidates never affect canonical results.
- Missing, stale, malformed, or widened projection data fails readiness with HTTP 503.

Completion evidence (2026-09-11): the strict loader builds one 142-document catalog with 100 typed
provisional variants and 42 typed review families. All 42 exact family queries return within Top-5
(worst rank 2), BMW remains a variant at rank 1, Proton Saga remains noncanonical, family readiness
and v2 health metadata are live, and the complete host suite passes 182/182. Family API
serialization remains intentionally deferred to T47.3.

### T47.3 — Expose and render the discriminated debug contract `[frontend/backend]`

- [x] Add strict discriminated API models and projection version metadata. _(→FHK-R5,FHK-R11,FHK-R14)_
- [x] Render variant and family candidates distinctly with text-safe DOM operations. _(→FHK-R12)_

Files:

- `src/product_variant_resolver/schemas.py`
- `src/product_variant_resolver/service.py`
- `ui/index.html`
- `ui/app.js`
- `tests/ui/test_debug_ui.py`
- `tests/api/test_api.py`

Acceptance:

- Type-inapplicable IDs are absent rather than fabricated or overloaded.
- One shared debug limit bounds the combined result list.
- Default responses remain unchanged and debug markup-shaped values remain inert text.

Completion evidence (2026-09-11): OpenAPI publishes a two-branch `knowledge_type` discriminator;
family and variant responses contain only their applicable identity fields. A single request limit
bounds the mixed result list, Proton Saga is visible as family review evidence while remaining
canonical `no_match`, and markup-shaped values remain inert in the UI harness. Seventeen focused
API/UI tests and the complete 184-test host suite pass.

### T47.4 — Verify and document the Lite integration `[qa/doc_curator]`

- [ ] Run focused, complete, data-chain, evaluation, compile, Compose, and whitespace checks. _(→FHK-R7–R16)_
- [ ] Map each requirement to measured evidence and update project documentation. _(→FHK-R16)_

Files:

- `specs/family-level-human-knowledge/review.md`
- `specs/product-variant-resolver/review.md`
- `docs/evidence/family-level-human-knowledge-t47.md`
- `docs/PROJECT-LOG.md`
- `README.md`

Acceptance:

- QA proves family suggestions are debug-only and canonical metrics/results remain unchanged.
- Documentation states that exact-name self-retrieval is not independent quality evidence.
- All changes remain inside the `Product Variant Resolver` repository.

## Requirement traceability

| Requirement | Implemented/verified by |
|---|---|
| FHK-R1 | T47.1 registry/manifest verification and negative tests |
| FHK-R2 | T47.1 exact projection/skip accounting tests |
| FHK-R3 | T47.1 searchable-field allowlist tests |
| FHK-R4 | T47.1 frozen manifest and deterministic-output tests |
| FHK-R5 | T47.2 typed loader plus T47.3 discriminated API tests |
| FHK-R6 | T47.2 combined retriever tests |
| FHK-R7 | T47.2 42-family Top-5 smoke matrix |
| FHK-R8 | T47.2 existing BMW variant regression |
| FHK-R9 | T47.2 seven-hold/four-merge exclusion tests |
| FHK-R10 | T47.2 service and canonical-regression tests |
| FHK-R11 | T47.2–T47.3 API/default-minimization tests |
| FHK-R12 | T47.3 safe UI tests |
| FHK-R13 | T47.1–T47.2 negative/readiness tests |
| FHK-R14 | T47.2 health, trace, and version tests |
| FHK-R15 | T47.4 repository-diff and evaluation-boundary review |
| FHK-R16 | T47.4 complete QA chain and evidence |

## Deferred tasks

- T48: independently authored casting-grouped family retrieval evaluation.
- T49: PostgreSQL persistence and pgvector quality/latency measurement for the accepted source.
- T50+: additional completed yearly-list ingestion toward approximately 3,000 reviewable rows.
