# Human-storage file runtime runbook

Date:2026-09-15. Lite. This runbook operates the optional local file-backed service only. The normal
`Dockerfile`/`docker-compose.yml` API remains the default. Nothing here creates PostgreSQL,downloads
data,changes canonical answers or proves a production deployment.

## What this service is

`human-storage-file` starts the same product resolver behind an additional strict gate. The gate reads
the frozen142-document human-knowledge snapshot,checks its complete integrity before valid requests,
and exposes human candidates only when debug is enabled. Canonical RAG still owns the public answer.

The committed v2 profile is inseparable from the exact image that passed QA. This is deliberate:an
operator cannot silently rebuild different code and continue using an old approval file.

## Prerequisites and preflight

Run commands from the repository root with Docker Desktop running. Confirm that the committed package
is internally consistent and that the exact local image is present:

```bash
.venv/bin/python scripts/freeze_human_storage_runtime_package.py --check --check-image
docker compose -f docker-compose.human-storage.yml --profile human-storage config --quiet
```

Both commands must exit0. If`--check-image` says the image is missing or has a different ID,do not edit
`runtime/human-storage-file-v2/profile.json` and do not add a fallback. Build and freeze a new versioned
package through the repository workflow; the v2 directory is exclusive evidence and must not be
overwritten.

## Start and observe

Start only the optional service from the already verified image:

```bash
docker compose -f docker-compose.human-storage.yml --profile human-storage \
  up --detach --no-build --wait human-storage-file
curl --fail http://127.0.0.1:8001/health
```

A healthy response has HTTP200 and reports the human-storage dependency as ready,with version
`human-storage-profile-development-v1-1ac55edae809`. The profile is mounted read-only at
`/runtime/profile.json`; the container runs as`pvr`,uses a read-only root filesystem and publishes only
to loopback. No database environment variable or persistent volume should appear.

For a local debug check:

```bash
curl --fail --request POST http://127.0.0.1:8001/resolve \
  --header 'Content-Type: application/json' \
  --data '{"title":"2022 Chevy Nomad Red #101","debug":true}'
```

The debug response may contain human candidate/storage evidence. A normal request with`debug:false`
must not expose that internal evidence and retains the canonical response contract.

## Stop and clean up

Use the same dedicated Compose file and profile:

```bash
docker compose -f docker-compose.human-storage.yml --profile human-storage down --remove-orphans
```

This removes containers and the Compose network. The image and committed profile remain. There is no
database volume to delete.

## Failure handling

- If the host profile is missing,Compose must fail and must not create a directory at the requested
  path. Restore the tracked file from Git; do not substitute a newer or mutable profile.
- If health is503,read the structured health detail. A checksum/source/version failure requires a new
  reviewed package; do not disable integrity verification or automatically fall back.
- If the image ID differs,stop. Rebuilding with changed dependencies produces a different runtime
  authority even when the tag looks identical.
- If port8001 is occupied,set`PVR_HUMAN_STORAGE_HOST_PORT` to another local port before`up`; keep the
  bind address at`127.0.0.1`.
- The app latches unavailable after a runtime integrity failure. Correct the source cause,then restart;
  it intentionally does not recover silently inside the same process.

The isolated QA reproducer is`python scripts/verify_human_storage_runtime_package.py`,but it creates
short-lived services on ports18080/18081 and is intended for verification rather than daily operation.
Its owner label and cleanup guard prevent it from deleting unrelated Docker resources.

## Rebuild/versioning boundary

Never overwrite`runtime/human-storage-file-v2/`. A code,data,dependency or packaging change requires:
a new image build; a new committed implementation; new versioned freezer output/defaults; a fresh
pre-output manifest/profile; then a new isolated runtime report. This preserves the difference between
“the tag exists” and “these exact bytes passed.” PostgreSQL packaging,credentials,migrations,imports,
backups and durable volumes require a separate rollout specification.
