# Human-storage stale protocol repair — Lite review

Date: 2026-10-10. Verdict: **PASS** for the bounded compatibility repair. No storage rollout,
PostgreSQL write, model change or default-runtime activation occurred.

## Requirements traceability

| Requirement | Evidence | Result |
|---|---|---|
| HSPR-R1 | Existing v4 protocol, manifest, math artifact and selection report retain SHA-256 `31802b…`, `b7634f…`, `82c94a…`, `f52f85…` | PASS |
| HSPR-R2 | `retrieval.py` again hashes to frozen `2ef973…`; `load_identity_protocol()` succeeds | PASS |
| HSPR-R3 | Only unused structured metadata was removed; storage-only bridge admits exact hashes for three known wrappers | PASS |
| HSPR-R4 | The previously failing human-storage API file now passes all 18 expanded cases | PASS |
| HSPR-R5 | Compatibility checksum/source mutations and all existing profile/storage fault cases fail closed | PASS |

## Review findings

The initial one-line repair was necessary but not sufficient. It restored the protocol manifest,
then exposed a separate historical-source check in the v4 selection report. Reverting `api.py`,
`config.py` and `service.py` would remove valid Pointwise runtime work; editing the old report would
erase which implementation actually produced its metrics. The accepted design therefore leaves the
strict loader and all historical evidence untouched. A new storage-only loader binds their exact
byte hashes, verifies unchanged identity math sources, and accepts exactly one current hash for each
known wrapper. Any future edit requires an explicit new compatibility artifact.

`human_knowledge_storage_profile.REQUIRED_RUNTIME_SOURCES` now includes the bridge code and its JSON
allowlist, so a runnable profile cannot omit either. The committed historical runtime package is not
silently reactivated; a future real run still needs a new source/profile freeze. The ordinary v4
loader intentionally continues returning `selection runtime source is stale` for current wrappers,
preventing the bridge from becoming a global bypass.

## Verification

- 18/18 human-storage API cases pass, including byte-equivalent canonical responses, request-level
  integrity probes and sticky 503 behavior.
- 66/66 focused storage/profile/package/compatibility cases pass.
- 168/168 combined API, v4, retrieval, PostgreSQL adapter, config and neural-reranker regressions
  pass.
- Ruff and strict target-local MyPy pass; `git diff --check` passes.
- Repository-wide smoke crossed the prior failure point with no failure but was deliberately stopped
  at 4% after about eight minutes because it contains expensive offline evaluations. It is recorded
  as interrupted, not as a full-suite PASS.

Full evidence: `docs/evidence/human-storage-stale-protocol-repair.md`.
