# T49.4 — Optional human-storage runtime packaging evidence

Date:2026-09-15. Lite mode,main agent,no subagents. Verdict:PASS for the bounded file-backed package;
default rollout and PostgreSQL runtime NOT PERFORMED.

The task packages the existing HSP-2/HSP-4 file profile as an explicitly selected local service. It
does not improve retrieval quality or add data. The original`Dockerfile`,`.dockerignore` and
`docker-compose.yml` retain their IBR-T5 SHA-256 values`cdd23bf…17ab`,`3505763f…112f` and
`7c36ba02…12ee`; therefore historical`api:app` runtime evidence and the ordinary Compose path remain
valid.

## Implementation and pre-output freeze

Commit`ae8a0e7` added the separately named Dockerfile/ignore/Compose files,the runtime freezer and
verifier,static tests and T49.4 spec. The dedicated service is behind profile`human-storage`,mounts one
explicit profile read-only,runs one Uvicorn worker as nonroot,and has read-only root/tmpfs/loopback-only
boundaries. It has no database URL,credential or persistent volume.

The first image/freeze exposed an honest packaging failure. Missing-profile rejection and cleanup
worked,but normal startup found that the strict v4 math verifier recursively reads
`reports/family-retrieval-development-v1/selection.json`. The original allowlist had only direct
storage-profile inputs,so run-v1 failed before comparison. Its sanitized report remains at
`reports/human-storage-runtime-package-v1.json`,SHA`3624c516…d37`; it contains no credential.

Commit`e80d845` explicitly added the required transitive selection/plan evidence and its producers to
the dedicated allowlist. It did not copy all reports or weaken integrity. The corrected image is
`sha256:d8ccf54d58931a0ec41276d659e117de6a935c58d962d8f146ea2b2d8450e718`(74,553,155 bytes,
user`pvr`). Commit`d3bf29e` then froze v2 before runtime output:

- manifest SHA`b89dfbc4bb7bc3162322c736c31d6a23b5b656b6534ac96731bc9d7f1016d624`;
- profile SHA`a51d3112031c638e9744163fe5f1614fb31009fe2bb23dd17e378e56e4a8980a`;
- owner project`pvr-t49-4-runtime-2a136c10e4e1`;
- implementation commit`e80d845ed0d2535bd404b6a3fe4f89fb3944acca`.

## Isolated Docker result

The verifier ran from2026-09-15 15:23:21–15:23:29 UTC. Raw report
`reports/human-storage-runtime-package-v2.json` has SHA-256
`bac44242f94b3a41059e681dde0c2b10ec176e994d852cc77753526e678b761c` and verdict PASS.

Before normal startup it substituted a nonexistent profile path. Compose exited1,the missing path was
not created,and only hashed stderr was retained. It then started`default-reference` and
`human-storage-file` from the exact frozen image. Both health endpoints returned200. Storage readiness
was true with version`human-storage-profile-development-v1-1ac55edae809`; debug returned its profile
SHA and integrity timing.

Four normal requests—`2022 Chevy Nomad Red #101`,`Toyota Supra`,`Chevy Nomad`,and`red toy boxed`—each
returned200 from both services and had identical normalized-response SHA. This verifies the selected
package did not change public canonical responses; it is not an accuracy benchmark. Docker inspect
confirmed both containers used the exact image,`pvr`and read-only root. Host bindings were
`127.0.0.1:18080/18081`; the storage profile mount was read-only. Cleanup errors and remaining owned
resources were both empty.

## QA and claim boundary

`PYTHONPATH=src .venv/bin/pytest -q` collected and passed559 tests. The focused packaging/storage/API/
frozen-v4 set passed71. Strict isolated MyPy for the two new scripts,compileall,changed-Python Ruff F/I,
and dedicated Compose config validation passed. One existing Starlette/AnyIO deprecation warning
remains. One accidental command supplied`Dockerfile.human-storage` to Ruff as Python and naturally
reported syntax errors; the applicable Python-only Ruff command passed,while the Dockerfile itself
successfully built and its Compose configuration ran.

This evidence covers local Docker on ARM64,file snapshot142,one worker and sequential smoke requests.
It does not prove PostgreSQL packaging,remote/TLS traffic,concurrency,durability,production SLA,
3,000-document cost/source rights,or release-level color/wheel/tampo accuracy. The next product-data
step is separately specified VAR-PLAN1 field-evidence review.
