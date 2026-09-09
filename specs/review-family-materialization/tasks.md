# Review-Family Materialization — Tasks

> Mode: Lite / Lean Industrial
>
> Status: Complete

## Task order

### T46.1 — Build the deterministic review-family registry `[backend]`

- [x] Implement `scripts/build_review_family_registry.py`. _(→RFM-R1–RFM-R9, RFM-R11–RFM-R13)_
- [x] Generate the registry, manifest, and readable materialization report. _(→RFM-R9–RFM-R10)_

Files:

- `scripts/build_review_family_registry.py`
- `data/review_family_registry.json`
- `data/review_family_registry_manifest.json`
- `reports/review-family-materialization.md`

Acceptance:

- The final T44 queue, staging dataset, existing human catalog, and all three frozen manifests are
  verified before output.
- Output contains exactly 42 new family entities, 4 existing-family merge links, and 7 explicit
  hold exclusions.
- The 100 source rows occur exactly once as held release references with a 79/9/12 class split.
- New UUIDs derive only from the fixed namespace and immutable family review ID.
- No provisional variant, canonical identity, runtime index, or PostgreSQL row is created.

### T46.2 — Add fail-closed registry validation and deterministic tests `[backend/qa]`

- [x] Add focused unit and artifact tests. _(→RFM-R3–RFM-R13)_
- [x] Extend fixture validation to verify registry and manifest checksums/boundaries. _(→RFM-R10–RFM-R13)_

Files:

- `tests/test_review_family_registry.py`
- `scripts/validate_fixture_data.py`
- `data/manifest.json` if the project-wide manifest owns the new artifacts

Acceptance:

- Tests cover exact counts, IDs, aliases, provenance, merge targets, hold exclusion, variant hold,
  output hashes, and byte-identical regeneration.
- Changed/incomplete inputs, pending decisions, duplicate source rows, unknown merge targets,
  unapproved aliases, and widened variant scope all fail closed.
- `--check` performs no writes.

### T46.3 — Verify and document the materialization milestone `[qa/doc_curator]`

- [x] Run focused and complete test suites plus the full deterministic data chain. _(→RFM-R1–RFM-R13)_
- [x] Update README, QA review, evidence, decision history, and project log with measured results.

Files:

- `README.md`
- `specs/review-family-materialization/review.md`
- `specs/product-variant-resolver/review.md`
- `docs/evidence/review-family-materialization-t46.md`
- `docs/PROJECT-LOG.md`

Acceptance:

- QA maps every RFM requirement to a passing test or artifact check.
- Documentation distinguishes family materialization from variant approval, runtime indexing,
  canonical promotion, and PostgreSQL ingestion.
- All changes remain inside the `Product Variant Resolver` repository.

## Explicitly deferred tasks

- T47: specify and implement family-level documents in the human-knowledge Dual-RAG source.
- T48: create an independent casting-grouped holdout evaluation for the enlarged source.
- T49: design PostgreSQL persistence and measure pgvector retrieval at the expanded scale.
- T50+: ingest additional completed yearly lists toward approximately 3,000 reviewable rows only
  after T46–T49 preserve quality and identity boundaries.

## Requirement traceability

| Requirement | Implemented/verified by |
|---|---|
| RFM-R1 | T46.1 input verification; T46.2 changed-checksum and queue-state tests |
| RFM-R2 | T46.1 partition validation; T46.2 decision-vocabulary tests |
| RFM-R3 | T46.1 entity builder; T46.2 UUID/ID stability tests |
| RFM-R4 | T46.1 merge-link builder; T46.2 target-resolution tests |
| RFM-R5 | T46.1 exclusion builder; T46.2 held-name leakage tests |
| RFM-R6 | T46.1 held release references; T46.2 no-fabricated-variant tests |
| RFM-R7 | T46.1 alias builder; T46.2 conservative-alias tests |
| RFM-R8 | T46.1 provenance projection; T46.2 provenance completeness tests |
| RFM-R9 | T46.1 serializer; T46.2 byte-identical regeneration tests |
| RFM-R10 | T46.1 manifest/report; T46.2 exact accounting and checksum tests |
| RFM-R11 | T46.1 pre-write validation; T46.2 negative-path tests |
| RFM-R12 | T46.2 boundary tests; T46.3 repository-diff review |
| RFM-R13 | T46.1 check mode; T46.2 non-mutating check-mode test |
