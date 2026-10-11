# Runtime Packages

This directory stores frozen metadata for the optional human-storage file profiles. It is not a
record of a live production deployment.

- `human-storage-file-v1/` and `human-storage-file-v2/` retain profile, manifest, and package notes.
- The default API does not automatically select these profiles.
- Exact source hashes and compatibility checks fail closed when a wrapper changes.
- PostgreSQL rollout, production networking, and a persistent managed service are not established.

See the [historical runbook](../docs/runbooks/human-storage-file-runtime.md) only when reproducing
that optional profile. For the current architecture, start with the
[system overview](../docs/architecture/system-overview.md).

