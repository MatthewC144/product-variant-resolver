# T49.4 — Human-storage runtime packaging design

## Overview and architecture

Keep the existing Dockerfile/Compose and`api` service byte-unchanged. Add a dedicated
`Dockerfile.human-storage` and`docker-compose.human-storage.yml`; its`human-storage-file` service is
behind profile`human-storage`. It runs the existing explicit app entrypoint and bind-mounts one profile at
`/runtime/profile.json`; no PostgreSQL service is started. The profile is generated only after the
image is built and binds that content-addressed image ID plus the unchanged T49.3 source/snapshot/math
hashes. This avoids embedding an image's own ID inside itself.

```text
existing compose up api ────────────► original frozen api:app package
dedicated compose default-reference ► new image running api:app
--profile human-storage + mount ────► new image running human_knowledge_storage_app:app
                                           │
                                           └─ strict142 file snapshot + per-request integrity
```

## Interfaces and data

Host input:`runtime/human-storage-file-v2/profile.json` after the retained v1 missing-dependency
failure. Container input:`/runtime/profile.json` via
read-only bind with`create_host_path:false`. Environment variable
`PVR_HUMAN_STORAGE_PROFILE_HOST_PATH` may select another explicit host file for verification; the app
always receives`PVR_HUMAN_STORAGE_PROFILE_PATH=/runtime/profile.json`. Host port defaults to8001 and
binds127.0.0.1 only. Package manifest records image ID,profile SHA,source commit,Compose service/profile,
entrypoint and packaging-source hashes.

A Dockerfile-specific ignore file admits only the four external JSON inputs required by the frozen
source manifest and both required protocol producers. Under`reports/`, only the v3 development
selection JSON/Markdown,the v4 selection JSON and snapshot plan are sent to the image. This prevents
future QA reports from perturbing the runtime image
while preserving the historical Dockerfile,ignore and Compose hashes.

## Error handling and safety

A missing host profile is rejected by Compose rather than created as a directory. Malformed/stale
content is rejected by the existing strict loader and reports503/not-ready; no fallback is added.
The runtime verifier uses a unique Compose project,refuses pre-existing resources with that label,
records only hashes for failed subprocess output and always tears down that exact project. No volumes,
PostgreSQL or credentials are involved.

## Testing strategy and trade-offs

Static tests cover dedicated Compose opt-in/default isolation,Docker context allowlist,freeze validation and
cleanup guards. Runtime smoke starts default and optional services from the exact frozen image,checks
health/debug/nondebug parity and container properties,then confirms zero labeled residue. Full tests,
Ruff F/I,MyPy and compileall remain required.

Only file mode is packaged. Packaging PostgreSQL now would require relaxing the deliberately disposable
database-name guard and defining secret/migration/import lifecycle,which is a rollout decision outside
this closure. The file package proves operability without broadening authority; its cost is that DB
operation remains an isolated experiment rather than a persistent service.
