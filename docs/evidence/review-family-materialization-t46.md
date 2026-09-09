# T46 Review-Family Materialization — Verification Evidence

## Measured output

| Artifact state | Count |
|---|---:|
| Stable new review families | `42` |
| Existing human-family merge links | `4` |
| Non-indexable hold exclusions | `7` |
| Create / merge / hold source rows | `79 / 9 / 12` |
| Unique held release references | `100` |
| Provisional variants | `0` |
| Canonical promotions | `0` |
| Runtime-indexed families | `0` |
| PostgreSQL rows | `0` |

Registry SHA-256 is
`3f289b802cc2e8280ed5c3586d87cfabbee7ce37b10ae79504b5aa6b8837367d`; manifest SHA-256 is
`ae9eda741aa2ec7cb9354424e17b789ba73c05890859e73d19cd845c5cab3ff2`; readable report SHA-256 is
`5312f2b86b3209c815def09417628a0248a8e50251f88ec3a48aeb7ed03203b5`.

## Focused tests

```text
PYTHONPATH=src /opt/homebrew/bin/python3 -m unittest tests.test_review_family_registry -v
Ran 9 tests — OK
```

The tests verify exact counts, stable source-based UUIDv5 identities, conservative aliases, exact
merge targets, named hold exclusion, complete provenance, 100-row unique coverage, zero fabricated
variant/canonical fields, frozen output hashes, non-mutating `--check`, and fail-closed checksum,
queue-state, scope, duplicate-row, unknown-target, and identity-collision cases.

## Complete verification

```text
PYTHONPATH=src /opt/homebrew/bin/python3 -m unittest discover -s tests -p 'test_*.py' -q
Ran 168 tests in 1.500s — OK
```

The host Python 3.14 interpreter emitted the already documented Starlette legacy-`httpx`
TestClient warning. The constrained Python 3.12 container path was previously verified with
`httpx2`; the warning did not fail or alter this run.

The following checks also exited zero:

- project fixture and 100-row Wiki pilot validators;
- deterministic Wiki review, base queue, priority-one evidence/decisions;
- all five priority-two research and all five priority-two decision checkpoints;
- `python3 scripts/build_review_family_registry.py --check`;
- Python compilation for `src`, `scripts`, `tests`, and `migrations`;
- default and PostgreSQL-profile Docker Compose configuration;
- `git diff --check`.

The global fixture validator now includes registry checksum, count, UUID, alias, merge-target, hold,
release-coverage, source revision/license, and zero-promotion/index/persistence checks. Its combined
fixture checksum after T46 is
`2c72ca83a74e090d8e89e6df124fb1520355643fd8629f71535f099269d45972`.

## Boundary proof

The implementation changes only the new builder/test/registry/report, fixture validator, and
documentation. It does not modify `src/product_variant_resolver`, the canonical or human-backed
runtime catalogs, API schemas, migrations, evaluation/calibration artifacts, or Compose services.
Consequently, the registry is inspectable and reproducible but not yet searched by Dual-RAG or
stored in PostgreSQL.
