# Human-storage stale protocol repair evidence

Date: 2026-10-10. Mode: Lite / Lean Industrial. Main agent only; no subagents. Verdict: PASS for the
bounded repair.

## Problem and root cause

The DRV2 closure smoke had reported 13 failures in the optional T49.3 human-storage API. The app did
not reach request handling: startup caught a v4 integrity exception, left `app.state.service=None`,
and correctly returned 503. The first cause was a later unused
`StructuredRetriever.version = "structured-v1"` line. It changed `retrieval.py` from the frozen
SHA-256 `2ef9737d…06c1` to `5ec6ae31…5084` even though no source consumed that attribute.

Removing that one line restored the exact frozen file and made `load_identity_protocol()` pass. It
then exposed the deeper cause: the 2026-09 v4 selection report also pins historical hashes for
`api.py`, `config.py` and `service.py`. Those files later gained typed error details and the governed
neural Pointwise provider/configuration. The selection report had never evaluated those wrapper
versions, so its strict loader correctly rejected them.

## Code and artifact decision

Historical protocol/report/artifact bytes were not changed, and the three current wrappers were not
reverted. Instead, `human_storage_v4_compatibility.py` implements a narrow adapter used only by
`human_knowledge_storage_app.py`. Its JSON allowlist has file SHA-256
`532da37ed79280b2aa047766ad9aaaa1aeec51f12ab756e3d250cdeb4e3d86bd` and records:

- exact hashes for the old protocol, manifest, math artifact and selection report;
- the complete historical selection source map;
- unchanged hashes for identity math, artifact validation, retrieval, schema and UI sources;
- exactly one accepted current hash for `api.py`, `config.py` and `service.py`;
- explicit prohibitions against refreezing history, changing v4 math or enabling default runtime.

The adapter checks those bindings, the four configured corpus/development inputs, fixed v4
parameters, the frozen winner and configuration summaries. It does not claim the old benchmark ran
against new wrappers. That historical claim still belongs to the old strict loader; current API
parity is established separately by tests. This is preferable to a semantic/wildcard exception:
the next wrapper edit fails closed until another reviewed compatibility version exists.

`REQUIRED_RUNTIME_SOURCES` now includes both the module and JSON artifact. This means private test
profiles pin the bridge and future real profiles must explicitly freeze it. Existing historical
runtime evidence remains historical; this task did not rebuild images or activate a deployment.

## Verification results

Commands and outcomes:

- `.venv/bin/python -m pytest tests/api/test_human_knowledge_storage_api.py -q`: 18 passed.
- Focused compatibility/storage/profile/runtime-package set: 66 passed.
- Combined v4 artifact, retrieval, PostgreSQL adapter, config, API, storage and neural-reranker set:
  168 passed.
- Ruff on changed Python/tests: PASS.
- strict MyPy on the new loader, storage app/profile and tests: PASS.
- `git diff --check`: PASS.

The negative tests prove compatibility-file checksum drift and an unlisted current wrapper hash both
reject. Existing tests retain invalid-profile, changed snapshot, missing database, SQL failure,
post-start corruption, process-lifetime latch and no-fallback behavior. The original strict v4 loader
still rejects current wrapper drift, demonstrating that no global verification bypass was introduced.

A repository-wide smoke was also started. It crossed the previous roughly 100-test failure point
without a failure but reached only 4% after about eight minutes because later suites execute costly
offline evaluations; it was interrupted to honor Lite mode. This is not represented as a full-suite
PASS. The directly affected 168-case regression set is the scoped G3* evidence.

## Remaining boundary

The optional storage path is repaired for exact current sources and private profile validation. A
new real file/PostgreSQL runtime run would still require a newly frozen source profile/package; this
task did not authorize one. Default FastAPI behavior, v4 parameters, catalog content, Pointwise model,
thresholds and domain-ranker result are unchanged.
