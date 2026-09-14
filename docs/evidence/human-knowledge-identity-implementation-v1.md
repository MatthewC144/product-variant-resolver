# IBR-T2 — Isolated v4 implementation checkpoint

Date: 2026-09-14. Mode: Lite, no subagents. Engineering scope: IBR-T2 only.
Algorithm/wiring checkpoint: PASS. Development quality/cost/final verdict: NOT EVALUATED.

## What was implemented

`human_knowledge_identity.py` indexes only provisional casting and family casting/approved aliases.
The unchanged frozen policy removes whole listing-noise tokens. Complete approved-core token sets
produce sparse IDF evidence; character bigram/trigram postings store normalized form weights using
document-level DF. Query norms retain unknown grams. Direct posting dot accumulation and max per
document equal the independent all-form cosine oracle, without approximate preselection.

Each channel retains at most 25 documents, dense scores only their union (at most 50), and weighted
RRF preserves missing source ranks and UUID tie-breaking. Query length/token/window/posting caps
abort the entire human result; canonical retrieval still runs. Invalid index/provider state instead
raises dependency failure. All work counters are immutable query-return values, not shared last state.

`human_knowledge_identity_artifact.py` separates admission evidence parsing from query arithmetic.
Runtime opt-in pins the protocol/manifest and every historical source/file, configured corpora and
development checksums, policy/limits/grid/fixed hashing parameters, report/runtime implementation
checksums, 21 raw configurations, 199/120 case counts, candidate ranks/fusion/work, recomputed metrics,
cost percentiles, scale target hits and the qualified deterministic winner. It never runs retrieval.
The future T3 implementation/report are mandatory; no such qualified report exists now.

Settings/service expose a separate `PVR_HUMAN_KNOWLEDGE_IDENTITY_ARTIFACT`; simultaneous v3/v4
settings fail. Invalid opt-in yields health/resolve 503 without implicit fallback. Default remains v2.
API debug/health and safe-text UI reveal v4 index/form/work/policy evidence, while older payloads omit
the new work field. Final identity/status/confidence/policy remain canonical-only and debug-off equality
is tested. Docker context now includes the source-bound builder/reports; this is static packaging only.

## Produced verification

- Focused core/artifact/API/UI: **65 passed**, including 63 new tests and two existing DOM checks.
- Full repository: **311 passed**, no skips; one existing Starlette/AnyIO deprecation warning.
- Focused Ruff `F,I`: PASS. Isolated strict MyPy `--follow-imports=skip` over the two new modules,
  config and service: PASS. This is not a claim that all repository lint/type debt is resolved.
- Python compilation, `node --check ui/app.js`, `git diff --check`: PASS.
- Default and `--profile postgres` Compose configuration validation: PASS; no image/container run.
- Frozen identity protocol and old 199-case development checks: PASS.
- Old v3 JSON/Markdown checks and old v1 final JSON/Markdown reproduction: PASS, unchanged FAILs.

Representative commands (run from the independent project root):

```bash
PYTHONPATH=src .venv/bin/pytest -o addopts='' -q
PYTHONPATH=src .venv/bin/python scripts/build_human_knowledge_identity_protocol.py --check
PYTHONPATH=src .venv/bin/python scripts/build_family_retrieval_development.py --check
PYTHONPATH=src .venv/bin/python -m product_variant_resolver.human_knowledge_selection --check
PYTHONPATH=src .venv/bin/python scripts/generate_human_knowledge_selection_report.py --check
PYTHONPATH=src .venv/bin/python -m product_variant_resolver.human_knowledge_evaluation --check
PYTHONPATH=src .venv/bin/python scripts/generate_family_retrieval_report.py --check
docker compose config --quiet
docker compose --profile postgres config --quiet
```

Tests cover unknown-gram norms/document-vs-form DF, complete/partial/broad-field admission, character-
only typo ranks, deterministic UUID/RRF arithmetic, source/union bounds, invalid/empty/excessive forms,
query/window/posting caps and exact visit boundary, nonfinite dense failure, immutable work, sequential
and four-thread in-process metadata isolation, API opt-in/readiness and canonical equality. The DOM
harness verifies new work evidence and malicious markup remain inert text.

Artifact parser success-path tests deliberately mock a qualified winner/report validation and use
temporary in-memory fixture evidence. They are not real selection results or quality/performance
proof. Negative tests reject stale/missing/boundary/parameter/no-winner evidence; raw candidate tests
recompute actual tiny-corpus ranks and reject altered identity, rank, admission score or fusion.
Complete real raw-report replay belongs to T3. A concurrency correctness smoke is not load testing.

## Corrections, limits and handoff

The first full test command omitted `PYTHONPATH=src`, so an existing report subprocess could not import
the package. Repeating with the project source path passed; no frozen report was regenerated. An
initial Compose override command named nonexistent files; corrected validation uses the actual
single `docker-compose.yml` and its PostgreSQL profile. Neither is runtime evidence.

The approved noise policy, numeric synthetic cores/wrapper-only edit limitation, source checksums,
query ceilings and 21-setting grid are unchanged. No retrieval of the 199-case grid, latency sampling,
selected v4 artifact, new final authoring, SQL promotion or 3,000-real-row expansion occurred.
IBR-T3 is next: execute/freeze full raw development and scale results, apply every existing gate,
and stop on FAIL. Only a qualified winner committed before authoring can unblock T4/T5/T49.
