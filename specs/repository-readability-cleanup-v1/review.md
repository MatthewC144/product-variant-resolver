# Repository Readability Cleanup v1 — QA Review

Verdict: **PASS**  
Mode: Lite / Lean Industrial  
Scope: repository presentation, navigation, claim consistency, and active-core static quality.

## Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| R1–R3 | 194-line README; claim test reads frozen dual-source JSON | PASS |
| R4 | docs index, system overview, Code Tour, Results, Limitations, archive entry | PASS |
| R5 | Portfolio Guide uses the same headline, denominator, and guardrails | PASS |
| R6 | Mermaid pipeline and component rationale | PASS |
| R7 | Artifact policy inventories retained binaries/reports and migration boundary | PASS |
| R8 | Ruff zero; strict MyPy zero on six active-core modules | PASS |
| R9 | Four documentation claim/link tests | PASS |
| R10 | Focused API/retrieval/catalog and historical compatibility tests | PASS |
| R11 | Decision D75, evidence, Project Log, and this review | PASS |

## Verification

- Focused pytest: **83 passed**, one upstream Starlette/AnyIO deprecation warning.
- Ruff: **all checks passed** across active core, compatibility bridge, and changed tests.
- Strict MyPy: **success, no issues in 6 source files**.
- Public documentation link validation: PASS.
- README size: 194 lines, inside the 150–250 target.
- Public README/Portfolio Guide Dual-RAG wording: zero occurrences.
- `git diff --check`: PASS.
- Secret scan: no known API key, private-key header, or tracked `.env` found.

## Runtime and evidence boundary

The only active-core edits are typing/static-quality changes: a modern return annotation, a precise
optional-dependency type suppression, and `typing.cast` at the existing structured-retriever
composition point. Candidate scores, candidate order, model selection, thresholds, policies,
datasets, canonical authority, and runtime defaults are unchanged.

Because `service.py` is an exact-hash storage wrapper, its new non-runtime type-only SHA was added to
the existing current-wrapper allowlist. The historical selection hashes, identity math sources, and
unchanged `retrieval.py` hash remain intact; compatibility and API parity tests pass.

## Findings and deferred work

- Whole-repository Ruff/MyPy debt remains outside this cleanup; the active six-file runtime path is
  green.
- Four retained model checkpoints and large historical reports keep `.git` around 327 MiB. No
  binary was silently deleted or migrated; Git LFS/Releases is a separate P2 decision.
- Historical documents still contain original acronyms and terminology. This is intentional
  preservation, not the public positioning.
- No full final holdout, training, benchmark, or model evaluation was rerun.

