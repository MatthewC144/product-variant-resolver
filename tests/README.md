# Test Suite Map

| Directory | Coverage |
|---|---|
| `unit/` | Signals, identity, retrieval, ranking, calibration, policy, and storage units |
| `integration/` | Catalog, ingestion, PostgreSQL adapters, and cross-module contracts |
| `api/` | FastAPI behavior, health, fail-closed dependencies, and optional storage parity |
| `evaluation/` | Frozen datasets, manifests, model selection, privacy, and historical compatibility |
| `authority/` | Catalog proposal/review/authority transitions |
| `ui/` | Minimal local UI contract |
| `docs/` | Portfolio claims, links, terminology, and repository hygiene |

The default command is:

```bash
.venv/bin/pytest
```

Historical source-byte replay tests may be explicitly skipped when they compare a current wrapper
to an older experiment commit. Replacement compatibility tests still verify the original commit
binding and the exact current allowlist; skips do not authorize rewriting frozen evidence.

