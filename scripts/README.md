# Script Map

These scripts reconstruct datasets, reports, storage experiments, and governance artifacts. They are
maintenance/experiment tools, not commands that run automatically in the FastAPI service.

## Recommended entry points

Installed `pvr-*` commands are declared in [`pyproject.toml`](../pyproject.toml). Use those when an
equivalent command exists because their package interfaces are tested.

## Script families

| Prefix | Purpose |
|---|---|
| `generate_`, `build_`, `author_`, `prepare_` | Deterministic artifact construction |
| `validate_`, `verify_` | Read-only contract and integrity checks |
| `freeze_` | Version/hash-bound artifact materialization; requires the matching spec/authorization |
| `record_`, `apply_` | Owner-reviewed state transitions; never run casually |
| `run_`, `measure_`, `score_` | Bounded database, cost, or evaluation protocols |

## External-source scripts

Scripts with `fandom` in their name belong to historical, permission-gated source research. Their
presence is not current permission to crawl, does not run during tests, and does not define the
current dataset collection path. Follow source terms, project authorization, and the relevant
historical spec before any network action.

## Safety

- Never place API keys or database credentials in scripts.
- Do not rerun frozen final evaluations merely because a script exists.
- Prefer `--check` or validator modes when available.
- Local outputs must follow `.gitignore`; only approved aggregate/versioned artifacts belong in Git.

