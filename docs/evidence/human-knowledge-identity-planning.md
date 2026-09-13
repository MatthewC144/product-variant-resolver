# Identity-Bounded Retrieval — Lite Planning Checkpoint

Date: 2026-09-13. Scope: documentation proposal only.
Document consistency checkpoint: PASS. G1* owner approval: PENDING.
V4 engineering/quality/performance: NOT IMPLEMENTED / NOT EVALUATED.

## Produced plan and coverage

The new [requirements](../../specs/human-knowledge-identity-bounded-retrieval/requirements.md),
[design](../../specs/human-knowledge-identity-bounded-retrieval/design.md) and
[tasks](../../specs/human-knowledge-identity-bounded-retrieval/tasks.md) define 16 observable
requirements and five ordered delivery tasks. Task R references refer to IBR requirements.

| Requirement group | Planned acceptance task |
|---|---|
| R1–R2 preservation / disclosed protocol freeze | T1, T3, T5 |
| R3–R8 identity fields, core evidence, formula, budgets, fusion | T1–T2 |
| R9–R12 selection, exact oracle, honest scale cost/correctness | T2–T3 |
| R13–R14 mandatory artifact / runtime / canonical isolation | T2–T3, T5 |
| R15 new output-blind final lifecycle | T4–T5 |
| R16 T49 guard | T5 |

Design includes normalization/field/noise contracts, exact posting formula, unknown-gram norms,
fixed limits, cap/error behavior, query-local counters, new artifact path/schema, unchanged grid/
gates, old development reuse disclosure, synthetic 120-query workload and correctness controls.
Alternatives/risks appear in D39. This is an inspected traceability mapping, not implemented tests.

## Verified baseline

Executed from the independent `Product Variant Resolver` repository:

```text
PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' -q
236 passed, 1 existing Starlette/AnyIO deprecation warning; no skips

PYTHONPATH=src .venv/bin/python -m product_variant_resolver.human_knowledge_selection --check
development selection FAIL; winner=None

.venv/bin/python scripts/generate_human_knowledge_selection_report.py --check
development Markdown report validated

.venv/bin/python scripts/build_family_retrieval_development.py --check
199 dev cases; historical retrieval_executed=false freeze valid

PYTHONPATH=src .venv/bin/python -m product_variant_resolver.human_knowledge_evaluation --check
historical v1 evaluation reproducible

git diff --check
pass
```

The v3 raw selection report remains SHA-256
`dcc0cd4e09ec5b20862cfee39b90d65a12bbd48a80f7da29c0fbacb0da267853`.
No source/script/test/data/report changes were made; only README, specs and documentation changed.
All outputs are inside the project folder. No subagent, new ranking run, profiler, network/model
download, container/SQL runtime, artifact activation or real data expansion occurred.

## Required handoff

Under spec-dev-loop Lite G1*, present requirements → design → tasks to the project owner and stop
before build until confirmed. After approval, T1 validates actual core/collision/form limits and
freezes a new protocol before output; it cannot silently discard invalid identity cores. Full old
failures, default v2 and T49 blockade remain in force. The baseline suite is not evidence that v4
will be safer/faster or that the new limits/workload pass.
