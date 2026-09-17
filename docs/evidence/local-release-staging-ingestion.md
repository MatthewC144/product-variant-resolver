# Local release staging ingestion — verification evidence

Date: 2026-09-16; portability recheck: 2026-09-17. Lite / Lean Industrial. Current gate: **PASS**.

The four owner-supplied workbooks were parsed offline into one deterministic review-only snapshot.
The checked artifact has content/batch checksum
`85dae23a1a302845f59b63450b9d90623b4c9893ddcde672bffc8eb5b53849af` and reports 1,763 staged
observations, 1,763 unique source IDs, 1,763 unique toy numbers, 678 casting names, 1,763 unknown
colors, 699 rows with variant notes, zero parse errors, zero reviewed variants and zero canonical
products. The four current `Releases` sheets are exactly 19 columns wide with 445/441/440/437 rows.

## Requirement-to-check trace

| Requirement | Check | Result |
|---|---|---|
| LRS-R1 | Fixed filenames/direct-parent and no-network snapshot assertions | PASS |
| LRS-R2 | Exact current counts/header plus malformed header/formula/extra-column/duplicate tests | PASS |
| LRS-R3–R5 | Provenance/raw fields/checksums, review authority and `NULL` color assertions | PASS |
| LRS-R6 | Repeated build and bundle round-trip equality | PASS |
| LRS-R7–R9 | Fake transaction tests plus disposable PostgreSQL migration/import/fault/readback/isolation verifier | PASS |
| LRS-R10–R11 | Exact report check and source-rights-state assertions | PASS |

Focused tests with all four local owner files passed 19/19 and the full repository suite passed
629/629. A temporary repo copy deliberately omitted `HW data/`: 17 portable tests passed and only the
two exact owner-data integrations skipped with an explicit reason. Those 17 checks build exact-shape
synthetic workbooks, exercise parser/transaction failures, and verify the committed public
manifest's batch ID, source checksums and 1,763-row/`NULL`-color aggregate. This keeps a
fresh clone testable without weakening runtime source-bound validation or committing the source XLSX.

Changed test/support Ruff F/I and compileall passed. Strict isolated MyPy for the two modules plus
SQL verifier and the artifact `--check` also remain PASS. Whole-repository Ruff separately reports
56 existing I001 findings, and pytest emits one existing Starlette/AnyIO deprecation warning.

## Real PostgreSQL evidence

An empty database named `pvr_lrs_bdfeef11fb63`, matching the verifier's disposable-name guard, was
created inside a temporary `pgvector/pgvector:pg16` container. The repository was mounted read-only.
The verifier applied `0001→0002→0003`, downgraded `0003→0002`, verified removal of the two staging
tables, and reapplied `0003`. PostgreSQL was 16.14; Python 3.12.14 used SQLAlchemy 2.0.52, Alembic
1.19.2 and psycopg 3.3.5.

The injected duplicate at ordinal 880 made 881 rows visible inside the transaction and raised a real
SQL uniqueness error. After rollback, both staging tables contained zero rows and all protected table
counts were unchanged. A normal import then inserted exactly one batch/1,763 rows; the second import
returned unchanged, exact readback matched the snapshot, every color remained `NULL`, and canonical
links stayed zero. Protected canonical/search/embedding/`hk_*` tables were zero before and after.
The container was stopped with `--rm`; a subsequent filtered container listing was empty, so the
disposable database and its container-layer storage were removed.

### Persistent local project import

After the disposable QA lifecycle passed, the same migration and frozen bundle were applied to the
project's normal local PostgreSQL volume. Migration head is `0003`. The first import returned
`inserted`; the immediately repeated import returned `unchanged`. Readback shows exactly 1 batch,
1,763 rows, 1,763 unique source IDs, 1,763 unique toy numbers, 678 casting names, 1,763 `NULL`
colors and zero canonical links. Per-year rows remain 2023=445, 2024=441, 2025=440 and 2026=437.

This local project volume is intentionally retained so development can continue from the staged
snapshot. It is not the disposable QA database described above, which was removed after its
rollback/migration checks. Retention does not promote any row: the persistent rows remain
review-only, outside canonical tables, evaluation labels and both Dual RAG runtime corpora.

## Closed counterexample

QA initially copied the inputs outside the repository, added `Unexpected` at `Releases!T6` and
`ignored` at `T7`, and demonstrated that the parser silently accepted them. Phase 2 then changed the
formula/input scanner to inspect the full populated row and reject any content after column 19. Two
regressions now reject both a twentieth-column value and a twentieth-column formula; the focused and
full suites pass. No production data files were changed, and the disposable copy was removed.

The parser-only fix leaves the normalized artifact checksum unchanged, so the real-SQL evidence
above remains applicable without creating another database.

The test evidence verifies staging mechanics only. It does not confer scraping permission,
republication rights, human verification, canonical product status, evaluation eligibility, or Dual
RAG runtime inclusion.
