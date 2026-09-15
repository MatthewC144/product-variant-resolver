# T49.3 HSP-3 — Isolated file/PostgreSQL correctness evidence

Date:2026-09-15. Lite mode, main agent, no subagents. Verdict:HSP-3 PASS; HSP-4 NOT RUN.

Owner「繼續執行下一步」followed the prior handoff that named HSP-3 and its new disposable SQL
resources. Four versioned run freezes were committed before their corresponding output attempts.
Only run-v4 is scored. It used database`pvr_t49_2_4f0b78ed2650`, internal network
`pvr-t49-3-4f0b78ed2650`, PostgreSQL image ID`sha256:131dcf…b74e6` and runner image
ID`sha256:7dbae1…c0fee`; no host port, persistent volume, production/default URL or old final105.

## Raw-first result

`reports/human-storage-profile-hsp3-raw-v4.json` (SHA-256`19301513cf057abd263564324cbb21158
ad2d0da7aa5e86f07a4d7f650ea0454`) was published as`raw_unscored` after resource cleanup. Only then
did the frozen scorer create`reports/human-storage-profile-hsp3-evaluation-v4.json`
(SHA-256`a6fdcb3433f97da62cbf64ebc10446cfd8e6f0b9116cec3d0d5b81566da20895`).
The evaluation reports exact parity199/199 across168positive,4merge,7hold and20unrelated cases.
All ranks/scores/discriminated candidate types/UUIDs/payload fields, character-index metadata and
identity work counters match. Canonical body projections for file and DB equal the unchanged default.
Every profile health check is200 and each case uses the same fixed request ID across all three calls.
There are21zero-candidate rows in each profile and they remain present in raw evidence.

## Safety and failure behavior

The generated application role can login but is not superuser, does not inherit, create roles or
create databases. Its only table grants are SELECT on the two human tables. Actual INSERT, UPDATE,
DELETE and TRUNCATE attempts all fail with SQLSTATE42501. Ten startup faults—missing/malformed/stale/
invalid file profile, unavailable/name-mismatched DB, missing/wrong-namespace/partial snapshot and
missing SELECT—produce health+resolve503. Post-start disconnect, header corruption, child deletion
and file-plan change produce503; restoring the source does not recover health/resolve without restart.
Malformed JSON400, content type415, blank/501-character/debug-disabled422 produce zero storage probes.
Canonical seven-table digest is`1d7b7f8a…bc172` both before and after all privileged fixtures.
The v4 two containers and network were removed; cleanup errors and remaining owned resources are empty.

## Retained implementation failures

Run-v1 stopped before case execution because PostgreSQL DDL cannot bind a role password as`$1`.
Its exception echoed an ephemeral credential; because secrets must not enter Git and its DB was already
destroyed, the sensitive file was removed and replaced by
`reports/human-storage-profile-hsp3-run-v1-failed-sanitized.json`. Run-v2 reached the failure matrix
then hit FK23503 while deleting header before children. Run-v3 reached the namespace fixture then hit
CHECK23514. Both raw failure files are retained and credential-free. Each fix was committed, followed
by a distinct pre-output freeze; no passing output overwrote or edited an earlier result.

Runtime:Linux aarch64,Python3.12.14,PostgreSQL16.14,SQLAlchemy2.0.52,Alembic1.20.0,psycopg3.3.5,
nonroot UID100. Focused59PASS; full548PASS; Ruff F/I, format, strict isolated MyPy and compileall PASS.
One pre-existing Starlette AnyIO alias deprecation remains. The roughly25.6-second end-to-end v4 run
is not a latency sample or SLA. HSP-4 still owns five startup samples/profile, warmups, paired HTTP/core
measurements and budget scoring; no3k, durability, concurrency, production or canonical-promotion claim.
