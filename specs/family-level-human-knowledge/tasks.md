# Family-Level Human Knowledge — Tasks

> Mode: Lite / Lean Industrial
>
> Status: Awaiting project-owner confirmation before build

## Task order

### T47.1 — Build the review-family runtime projection `[backend]`

- [ ] Implement the deterministic projection builder and non-mutating `--check`. _(→FHK-R1–R4,FHK-R13,FHK-R16)_
- [ ] Generate and freeze the 42-document projection and manifest. _(→FHK-R2–R4)_

Files:

- `scripts/build_review_family_knowledge.py`
- `data/review_family_knowledge.json`
- `data/review_family_knowledge_manifest.json`
- `tests/test_review_family_knowledge_projection.py`

Acceptance:

- Only T46 `new_families` become documents; 4 merges and 7 holds are accounted for but absent.
- Searchable fields are limited to brand/casting/approved aliases.
- Outputs reproduce byte for byte; invalid/stale/widened input cannot overwrite good output.

### T47.2 — Load typed documents into the combined v2 retriever `[backend]`

- [ ] Add strict family-projection/manifest loading and typed document models. _(→FHK-R5,FHK-R13–R14)_
- [ ] Generalize sparse/dense/RRF indexing to the shared 142-document pool. _(→FHK-R6–R10)_
- [ ] Add settings, startup readiness, version metadata, and bounded type counts. _(→FHK-R11,FHK-R13–R15)_

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

### T47.3 — Expose and render the discriminated debug contract `[frontend/backend]`

- [ ] Add strict discriminated API models and projection version metadata. _(→FHK-R5,FHK-R11,FHK-R14)_
- [ ] Render variant and family candidates distinctly with text-safe DOM operations. _(→FHK-R12)_

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
