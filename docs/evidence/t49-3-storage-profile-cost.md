# T49.3 HSP-4 — Frozen local storage-profile cost evidence

Date:2026-09-15. Lite mode, main agent, no subagents. Verdict:HSP-4 PASS and bounded T49.3 complete;
T49.4 NOT RUN.

Owner「繼續執行」followed the handoff that identified HSP-4 as the next step. The run remained inside
the approved cost protocol:local arm64,142 real human-knowledge documents,one worker,concurrency1,
five startup samples/profile,three warmups/profile and199 measured HTTP/core cases/profile. It did not
use the old final105,change a budget,perform a timed retry or claim a real3k/production workload.

## Raw-before-score execution

Run-v2 was frozen before output in
`data/evaluation/human-storage-profile-development-v1/hsp4-run-v2/`. It binds implementation commit
`31a97e43f9e051519f85c258faa68648d96cef33`, database`pvr_t49_2_a7fbc59ef861`, internal network
`pvr-t49-4-a7fbc59ef861`, the fixed199 pack/protocol, exact file/PostgreSQL profiles and content-addressed
PostgreSQL/runner images. The supervisor created only the labeled internal network, tmpfs PostgreSQL
and read-only/nonroot runner; there was no host port,persistent volume or production/default URL.

`reports/human-storage-profile-hsp4-raw-v2.json` was published as`raw_unscored` with SHA-256
`78e9eb938ff3615ebc3cf51418e9c06c463cf397a4f6138526863a0ced6c87ed`. It contains all10 startup
durations,12 warmup observations,398 measured HTTP results and398 measured core results, including
status,error,abstention and environment. No measured HTTP/core error occurred. Both containers and
the network were removed before scoring; cleanup errors and remaining owned resources are empty.

Only afterward did the independent scorer create
`reports/human-storage-profile-hsp4-evaluation-v2.json`, SHA-256
`af5ff062fb1f269f3b07ab27c9059a9d9ad31a4487f5ac131aadf724805dcccc`.

## Frozen-gate result

Nearest-rank values are milliseconds. With five startup samples,p95 is the slowest sample and should
not be interpreted as a long-running service distribution.

| Stage/profile | p50 | p95 | max | Frozen p95 ceiling | Result |
|---|---:|---:|---:|---:|---|
| Startup file | 255.271 | 271.142 | 271.142 | 5,000 | PASS |
| Startup PostgreSQL | 265.497 | 300.175 | 300.175 | 5,000 | PASS |
| HTTP file | 22.591 | 38.645 | 73.185 | 250 | PASS |
| HTTP PostgreSQL | 28.302 | 46.163 | 80.340 | 250 | PASS |
| Integrity file | 19.830 | 34.204 | 63.981 | 150 | PASS |
| Integrity PostgreSQL | 25.557 | 42.773 | 75.220 | 150 | PASS |
| Core file | 0.236 | 2.311 | 4.557 | 25 | PASS |
| Core PostgreSQL | 0.243 | 2.306 | 4.511 | 25 | PASS |

Startup times only cover profile factory construction through verified snapshot/cached-index readiness;
Python import,process/Docker/database bootstrap and OS cache eviction are excluded. HTTP is genuine
loopback Uvicorn and includes full-snapshot integrity,SQL/internal-network work,signal extraction,
canonical+human resolution,serialization and client parsing. Core starts from pre-extracted signals
against initialized indexes and excludes integrity,SQL/network,canonical resolution and HTTP.

Runtime:Linux6.12 arm64,Python3.12.14,PostgreSQL16.14,Uvicorn0.52.4,SQLAlchemy2.0.52,Alembic1.20.0,
psycopg3.3.5,runner UID100. Reader attributes are login true and superuser/inherit/create-role/
create-db false. The experiment imports100 provisional-variant plus42 review-family documents.

## Retained setup failure and verification

Run-v1 is retained as`reports/human-storage-profile-hsp4-raw-v1.json`. It failed before producing any
timing sample because the frozen runner image did not contain`httpx`; all v1 resources were still
removed and the file contains no password or database URL. The correction used Python's bundled
`urllib`, preserving the same image and HTTP timing boundary. It also made malformed/empty child
output a structured hashed runner failure. Code was committed before a separate v2 freeze; thresholds,
retrieval settings and data were unchanged, so v2 is not a budget rerun.

Focused storage-profile tests:79 PASS. Full suite:the first invocation without`PYTHONPATH=src` had
one known subprocess-import failure; the corrected established invocation`PYTHONPATH=src .venv/bin/pytest -q`
passed552/552 with one existing Starlette/AnyIO deprecation warning. Changed-file Ruff F/I,strict
isolated MyPy and compileall PASS. Whole-repo Ruff reports54 pre-existing import-order findings outside
this change and those unrelated files were not modified.

This evidence does not establish throughput,multi-worker behavior,durability,production SLA,3k scaling,
source rights or color/wheel/tampo/release-variant accuracy. T49.4 remains the next packaging and
operational-closure step; any default rollout still requires a separate decision.
