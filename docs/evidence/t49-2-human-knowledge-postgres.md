# T49.2 — Isolated PostgreSQL storage verification

Date:2026-09-14. Lite. Scoped T49.2 G2/G3*:PASS. Broader T49.3/runtime/production/collection gates WAIT.
Owner「執行測試」after [isolated environment proposal](../T49-2-ISOLATED-TEST-PLAN.md) authorizes
only its new disposable database, fixture baseline, human snapshot import and owned-resource cleanup.
No three independent broad G1 confirmations or future profile/schema rollout approvals are invented.

## Actual environment and immutable evidence

Raw report: `reports/human-knowledge-postgres-t49-2.json`, byte SHA256
`3450185e2f8b6d97b5b39c3e563265080e8f11d5b8db988bfd28fd448c22c39d`.
Actual execution:2026-09-14T22:38:29.394453Z–22:38:34.049015Z; this is a run window,
not a latency/throughput sample or performance gate. First actual SQL invocation PASS; no SQL retry.

PostgreSQL16.14/Linuxaarch64; runner Python3.12.14 UID100, read-only root, writable/tmp tmpfs,
read-only staged source bind. SQLAlchemy2.0.52/Alembic1.20.0/psycopg3.3.5. Local images only:

- pgvector/pgvector:pg16: `sha256:131dcf7ff6a900545df8e7e092c270aa8c6db2f2c818e408cb45ec21316b74e6`.
- product-variant-resolver:ibr-t5-rootfix:
  `sha256:7dbae114eb0615fb8582cce3fc79b2f19233edc453672bc5726de937dfec0fee`.

The runner reuses installed dependencies, not the old image's application sources:54needed Python/
migration/config/data/plan inputs are copied byte-exactly into a private staged tree with readable
copy modes and bound by report SHA256. Original600-mode files are not chmodded. No host SQL extra
installation, image download/rebuild or change to frozen Dockerfile/compose/source/UUID/final artifacts.
The supervisor rejects remote Docker contexts, uses a fresh ownership token, an internal network,
no published host ports, new PostgreSQL tmpfs and no persistent/old database volumes. Database
name was `pvr_t49_2_7bb34058d45b`; this test DB no longer exists after successful cleanup.

## Implemented storage contract

Additive Alembic0002 creates only `hk_snapshot` and `hk_document` after unchanged0001. Snapshot
metadata stores storage version, namespace, original plan header/source/contracts/counts/checksum
and imported_at. Child rows store original UUID/ID/type, ordinal, exact typed payload/checksum and
raw origin; PK/unique/FK/object/type/hash/count constraints reject invalid shapes. No embedding or
release tables yet. Adding0002 advances migration head; it does not modify canonical schema/history.
The historical T04 verifier is explicitly0001-revision-bound and is not claimed verified for newhead;
use this new dedicated verifier for0002, not its legacy `upgrade head` assertion of0001.

`human_knowledge_persistence.py` requires literal disposable authorization, a matching explicit
`pvr_t49_2_<12hex>` database name and actual server database match; there is no production URL/default
or .env lookup. The original source contract's `postgresql_ingestion` exclusion is preserved unchanged:
this separately authorized **human-knowledge-isolated-storage-test-v1** namespace is not canonical
ingestion permission. All142source-bound documents must validate before a transaction opens.

Imports hold SHARE ROW EXCLUSIVE locks on the two human tables in one transaction, serialize first
imports and prevent concurrent external table writes during verification. No canonical table locks/
mutation or update/delete/upsert repair path. Equal complete snapshot returns verified `unchanged`;
corrupt/partial stored snapshot fails closed. Reader selects explicit ID+content hash under a
repeatable-read read-only transaction, reconstructs the whole plan and verifies pinned local sources.

Application immutability/count completeness is enforced by the importer/reader, not a privileged
writer-proof database trigger. A superuser can manually corrupt/drop rows; tests simulate this only
in the new disposable DB and prove rejection/no repair. tmpfs correctness is not durable-storage,
crash/power-loss recovery, production role permissions, per-query SQL retrieval or query-cost evidence.
At142docs, serial table locks are deliberate simplicity; at10×, measure contention before claiming scale.
Transaction/lock reasoning uses [SQLAlchemy transaction documentation](https://docs.sqlalchemy.org/en/20/core/connections.html#using-transactions)
and [PostgreSQL16 locking documentation](https://www.postgresql.org/docs/16/explicit-locking.html).

## Actual SQL gates and counts

| Gate | Observed result |
|---|---|
| 0001→0002→0001→0002 cycle | New tables removed/restored; all canonical rows preserved |
| SQL unique fault after71visible documents + header | Full rollback to0snapshots/0documents |
| Simultaneous first imports | One `inserted`, one verified `unchanged`; one snapshot only |
| Stored142roundtrip |100provisional+42family, IDs/UUIDs/types/payloads/raw origins exact |
| Repeated import | All rows and imported_at byte-equivalent snapshots unchanged |
| Partial/duplicate/changed-payload/held input | Rejected; stored snapshot unchanged |
| Controlled stored-header corruption or missing child | Both reader/importer reject; no repair |
| Explicit mismatched/missing ID+hash | Rejected, no fallback/latest selection |
| Canonical before/after | Seven tables, every row/ID/timestamp unchanged |
| Owned resources cleanup | Two new containers + internal network removed, errors0, remaining0 |

Canonical fixture baseline ONLY in the fresh test DB:product_variant120/product_alias240/
identifier120/provenance_record120/index_metadata1/product_search120/product_embedding0.
Both canonical row-snapshot SHA256 values:
`ed4be9dc736c8ac476ca5fd2a66b4f5e4e104ed25583c98e6fd8c355f60b2daf`.
This includes dynamic fixture timestamps from this run; not a stable cross-run dataset checksum.
Original plan content SHA256 remains
`f7830e460650e99ab5107ec0f049c96d2dcf322daa5c140c5847a53f969e144f`.
No real dataset additions/canonical promotions/default profile changes or old final collector run.

## Commands actually verified

```sh
# Current evidence:read-only, does not create a DB or rerun SQL/final retrieval.
.venv/bin/python scripts/run_human_knowledge_postgres_test.py --check
PYTHONPATH=src .venv/bin/python -m pytest tests/test_human_knowledge_persistence.py tests/test_human_knowledge_postgres_test_runner.py
PYTHONPATH=src .venv/bin/python -m pytest
```

25new tests PASS; full473tests PASS with one existing Starlette/AnyIOBlockingPortal deprecation warning.
Focused RuffF/I, strict isolated MyPy on repository/supervisor, compilation and frozen plan/final
integrity checks PASS. Local fakes test orchestration only; the separate report proves real SQL.

For a separately desired fresh test, supply a **new** report filename; existing evidence is never overwritten:

```sh
.venv/bin/python scripts/run_human_knowledge_postgres_test.py --run --allow-disposable-test --output "$PWD/reports/human-knowledge-postgres-new-run.json"
```

The supervisor preserves stdout/stderr/failure evidence and cleans only exact IDs with matching
ownership labels, never old containers/networks/volumes. A process kill may leave owned resources;
there is no claim of crash-atomic Docker cleanup. Diagnose exact ownership before any cleanup.
Next T49.3 must freeze a new optional storage-profile/source/artifact/development-cost protocol;
do not modify scored v4 sources in place or reuse the105final questions for live selection/replay.
