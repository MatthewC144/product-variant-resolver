# Human-storage stale protocol repair — Design

Date: 2026-10-10. Mode: Lite / Lean Industrial.

## Diagnosis

The frozen v4 manifest requires `retrieval.py` SHA-256
`2ef9737d319b7d3ca6bdfd540e58147365eba4e2b6b4d47f1484fab3025f06c1`. A later Pointwise runtime
commit added only `StructuredRetriever.version = "structured-v1"`, changing the file SHA to
`5ec6ae31700dea0ed023620f14c2f80b5e14e055cd442e67f06907b9c6215084`. No source or test reads that
attribute. Removing it restores the protocol manifest and reveals a second, distinct guard: the
historical selection report pins `api.py`, `config.py` and `service.py` before the later Pointwise
runtime integration. Those current changes are legitimate and must not be reverted, but the old
report correctly refuses to pretend that it evaluated the new wrappers.

## Repair

Remove the unused class attribute. This restores the exact frozen bytes instead of weakening source
validation or rewriting historical protocol evidence. Retrieval interfaces and calculations are
unchanged; `StructuredRetriever` is passed separately from the versioned sparse/dense retriever
list and its version is never reported by the API.

Add a storage-only compatibility adapter and immutable JSON allowlist. The adapter validates the
exact old protocol, manifest, artifact and selection-report byte hashes; verifies that the identity
math, schema and UI sources still equal their historical hashes; and admits exactly one current
hash for each of `api.py`, `config.py` and `service.py`. It then reads the already-frozen winning
configuration without claiming that the historical evaluation ran against the newer wrappers.
The compatibility module and JSON file become mandatory storage-profile sources, so every runnable
profile also pins this new bridge. The original strict v4 loader remains unchanged for all other
callers.

This design intentionally separates two claims: the old report proves how the v4 parameters were
selected; the current API parity tests prove that the known wrapper revision preserves canonical
responses. Exact hashes make the bridge fail closed on the next edit. No Git history, network,
temporary source reconstruction or monkeypatching is required at runtime.

## Verification

Verify the exact file digest, direct v4 protocol load, compatibility-loader positive and mutation
cases, all human-storage API/profile/runtime tests, Pointwise runtime/retrieval regressions, Ruff,
MyPy/compileall and Git diff integrity. Existing negative integrity mutations must continue to fail
closed, while the original strict loader must continue rejecting the historically unevaluated
wrapper revisions.
