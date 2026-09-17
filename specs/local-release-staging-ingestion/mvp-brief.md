# Local release staging ingestion — MVP brief

Date: 2026-09-16; portability amendment: 2026-09-17. Mode: Lite / Lean Industrial.
Status: **complete**.

Owner authorization: 「請先幫我擴充．顏色部分若後續需要再考慮．」 This authorizes
offline processing of the four owner-supplied workbooks and isolated PostgreSQL release staging.
It does not authorize new network collection, canonical promotion, runtime RAG changes, or public
redistribution of the source workbooks.

## Purpose

Import `HW data/catalog-2023.xlsx` through `catalog-2026.xlsx` as one review-only release snapshot.
The 1,763 rows expand stored source evidence without entering `product_variant`, `hk_*`, canonical
search/embeddings, evaluation labels, or resolver answers. Missing colors remain `NULL`.

## Observable requirements

- **LRS-R1 — Fixed offline inputs.** WHEN an import plan is built, THE SYSTEM SHALL read only the
  four named local XLSX files and SHALL perform no network request.
- **LRS-R2 — Strict workbook contract.** WHEN a workbook is parsed, THE SYSTEM SHALL require the
  `Releases` sheet, the fixed 19-column header at row 6, one matching release year, and counts
  445/441/440/437 for 2023/2024/2025/2026 (1,763 total).
- **LRS-R3 — Preserve evidence.** WHEN a row is normalized, THE SYSTEM SHALL retain source record ID,
  typed catalog fields, source page/table/row, parse status/error, collection time, raw fields JSON,
  input filename, and input SHA-256.
- **LRS-R4 — Unknown color is valid.** WHILE `Color` is blank, THE SYSTEM SHALL store `NULL` and SHALL
  NOT infer color from `Variant note`, URL, model text, series, images, or general knowledge.
- **LRS-R5 — Review-only authority.** WHEN rows are staged, THE SYSTEM SHALL mark every row
  `needs_canonical_review` and `staging_only_not_evaluation_or_canonical`, with no canonical UUID.
- **LRS-R6 — Deterministic batch.** WHEN the same four bytes are parsed, THE SYSTEM SHALL produce the
  same batch ID, normalized payload, source checksums, row ordering, counts, and content checksum.
- **LRS-R7 — Atomic and idempotent SQL.** WHEN a valid batch is imported, THE SYSTEM SHALL commit the
  batch and all 1,763 records in one transaction; an identical repeat SHALL be a verified no-op.
- **LRS-R8 — Collision and rollback.** IF a batch ID already exists with another content checksum,
  or any record is invalid/colliding, THEN THE SYSTEM SHALL reject and roll back the whole import.
- **LRS-R9 — Storage isolation.** WHEN import completes or fails, THE SYSTEM SHALL leave canonical
  `product_variant`, aliases, identifiers, provenance, search, embeddings, and `hk_*` rows unchanged.
- **LRS-R10 — Honest reporting.** WHEN results are reported, THE SYSTEM SHALL distinguish 1,763 staged
  observations, unique toy numbers, casting names, unknown colors, reviewed variants, and canonical
  products; staged observations SHALL NOT be described as verified products.
- **LRS-R11 — Source boundary.** WHEN the owner-supplied exports are processed, THE SYSTEM SHALL record
  that access permission/republication rights were not provided and SHALL NOT treat local possession
  as permission for new scraping or public source-file publication.

## Design

```text
four local XLSX files
  -> strict read-only parser + cross-file validator
  -> deterministic normalized snapshot + manifest/report
  -> one PostgreSQL transaction
       release_source_batch (one immutable batch)
       release_source_record (1,763 review-only observations)
```

`release_source_batch` stores batch ID, schema/import versions, content checksum, exact per-file
checksums/counts/years, totals, source-rights state, and import timestamp. `release_source_record`
stores the 19 source columns as typed fields plus filename/checksum, `review_status`, `usage`, and
the batch foreign key. It uses `(batch_id, source_record_id)` as identity and unique batch/toy-number
protection. No foreign key targets canonical or human-knowledge identities.

The parser uses `openpyxl` read-only/data-only mode. It validates all inputs before opening a SQL
transaction. PostgreSQL code uses parameterized SQL and an additive Alembic `0003` migration.

## Error handling and boundaries

Missing files/sheets/columns, formula-only values, bad JSON, wrong year/count/order, blank required
fields, duplicate IDs/toy numbers, non-`parsed` rows, nonblank parse errors, malformed timestamps, or
checksum drift fail before SQL. SQL faults roll back. Blank color and variant note are permitted.
The import does not fetch Fandom, download images, change the API, or enable either RAG corpus.

## Testing strategy

Unit tests cover parsing, exact counts, null color, provenance preservation, deterministic hashes,
duplicates and tampering. Repository tests cover first import, identical no-op, batch collision,
mid-import rollback, and unchanged protected-table counts. A disposable PostgreSQL verification run
must apply migrations, import/read back 1,763 rows, repeat the import, inject one failure, and report
that protected tables are unchanged. Portable tests may generate exact-contract synthetic XLSX so a
fresh clone can verify parser and transaction behavior without the unpublished owner files; exact
owner-byte integrations skip explicitly when those files are absent. Synthetic support SHALL NOT
relax production source paths, checksums, artifact self-validation or row-count assertions. Full
pytest, Ruff, strict MyPy, and compileall remain green.

## Tasks

- [x] **LRS-T1** Implement the strict XLSX parser, normalized snapshot, manifest/report builder, and
  CLI using only the four local files. _(→LRS-R1–R6,R10–R11)_
- [x] **LRS-T2** Add migration `0003` and the transactional PostgreSQL staging repository/CLI.
  _(→LRS-R7–R9)_
- [x] **LRS-T3** Add focused unit/repository/real-SQL verification, including repeat and rollback.
  _(→LRS-R2–R10)_
- [x] **LRS-T4** Run focused/full QA and update review, evidence, AI eval, README, decision record,
  roadmap, and narrative `docs/PROJECT-LOG.md`. _(→LRS-R1–R11)_

## Acceptance

The delivered report shows exactly 1 batch, 1,763 staged rows, 1,763 unique source IDs and toy
numbers, 678 cross-year casting names, 1,763 `NULL` colors, zero parse errors, zero canonical/human
rows changed, and an identical second import adding zero rows. Source XLSX files remain local and
unpublished unless the owner later confirms redistribution rights.
