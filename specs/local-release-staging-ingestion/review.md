# Local release staging ingestion — QA review

Date: 2026-09-16; portability recheck: 2026-09-17. Mode: Lite / Lean Industrial.
Verdict: **PASS**.

## Checked items

| Requirement | Evidence and result |
|---|---|
| LRS-R1 | Parser accepts only the four direct `HW data/catalog-2023.xlsx`…`catalog-2026.xlsx` paths; artifact reports zero network requests. Exact owner-data checks run when those local files exist, while synthetic contract tests keep a fresh clone testable without publishing them. PASS. |
| LRS-R2 | Supplied workbooks have exactly 19 columns and expected 445/441/440/437 rows. Regression tests prove that a value or formula in column 20 is rejected instead of ignored. PASS. |
| LRS-R3–R5 | Focused tests and exact bundle check preserve typed/raw provenance, file checksum, review-only status, `NULL` colors, no canonical UUID, and staging-only usage. PASS. |
| LRS-R6 | Rebuilding the same four inputs yields the same snapshot, batch ID and content checksum; bundle round trip is exact. PASS. |
| LRS-R7–R9 | Disposable PostgreSQL verification proves one-transaction insert, identical verified no-op, genuine mid-import SQL rollback, exact readback, migration downgrade/upgrade, and unchanged protected tables. PASS. |
| LRS-R10–R11 | Report distinguishes 1,763 staged observations from zero reviewed/canonical products and records the missing access/republication permission boundary. PASS. |

## Findings

### Blocker

- None. The initial LRS-R2 extra-column finding was returned to Phase 2 and fixed before final review.
  The scanner now inspects all populated worksheet columns and the two new regressions pass.

### Important

- None for LRS-T1–T3.

### Later

- The full suite retains one pre-existing Starlette/AnyIO `DeprecationWarning`.
- Local strict MyPy initially could not resolve the declared optional PostgreSQL packages. After
  installing the project's `postgres` dependencies in `.venv`, strict isolated MyPy passed all three
  new source/verifier files.

## Reproduction and evidence

- Focused with all four owner files present: `PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' -q tests/unit/test_release_staging.py tests/test_postgres_release_staging.py` — 19/19 PASS.
- Portability simulation: the same source, tests and committed aggregate manifest/report were copied to a
  temporary repo without `HW data/`; the focused command returned 17 PASS / 2 explicit owner-data
  skips. Synthetic 1,763-row parsing, contract failures, repository transactions and committed
  artifact checksum/count validation therefore remain runnable in a fresh clone.
- Full: `PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' -q` — 629/629 PASS; one warning above.
- Changed-file Ruff F/I — PASS. Whole-repository Ruff — 56 existing I001 findings.
- Changed test/support compileall — PASS.
- Strict MyPy: `PYTHONPATH=src .venv/bin/mypy --strict --follow-imports=skip src/product_variant_resolver/release_staging.py src/product_variant_resolver/postgres_release_staging.py scripts/verify_release_staging_import.py` — PASS.
- `python -m compileall -q src tests scripts migrations` — PASS.
- `pvr-stage-releases ... --check` equivalent module command — PASS, batch/content SHA-256 `85dae23a1a302845f59b63450b9d90623b4c9893ddcde672bffc8eb5b53849af`.
- Real SQL: PostgreSQL 16.14 disposable database `pvr_lrs_bdfeef11fb63`; migration revision `0003`; 1 batch, 1,763 rows, 1,763 unique IDs/toy numbers, 678 castings, 1,763 `NULL` colors, zero canonical links. Insert/no-op/rollback/readback/isolation gates PASS.
- Cleanup: the PostgreSQL container used `--rm`, was stopped after verification, and a filtered
  `docker ps -a` returned no matching container. The disposable database no longer exists.

The post-fix artifact checksum is unchanged, and the fix touches only pre-SQL workbook rejection.
Therefore the successful disposable PostgreSQL result remains applicable; rerunning a destructive
database lifecycle would add no coverage.

## Closure and recommended next task

LRS-T4 documentation is complete: the decision record, README/roadmap, evidence and narrative project
log retain the distinction between 1,763 staged observations and zero verified/canonical products.
The next feature should define a separate, auditable human review/promotion workflow; color remains
unknown until reliable evidence can be attributed to a specific release row.
