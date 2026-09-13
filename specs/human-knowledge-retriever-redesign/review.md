# Human Knowledge Retriever Redesign — HRR-T3 Lite Checkpoint

Date: 2026-09-12. Scope: HRR-T1–T3 only, not whole-feature closure.

Engineering verification: PASS. Development selection: **FAIL**. HRR-T4–T6 and T49 remain blocked.

The evaluator executes the exact frozen 21-configuration grid and retains all 4,179 raw case/
configuration outputs. Ordered candidates precede development-label scoring. Report checks bind
inputs/code, validate typed corpus identities and source ranks/scores, recompute weighted RRF,
raw metrics, latency percentiles, rejection reasons and deterministic winner. No configuration
survives unrelated-control or cost gates, so `winner=null` and the freezer touches no artifact.
This completes the required conditional FAIL branch; it does not complete final-quality acceptance.

| Requirements | Evidence | Checkpoint result |
|---|---|---|
| R1–R3 | Frozen checksum/count/source checks; guarded no-v1 file reads; dev leakage disclosure | PASS |
| R4–R7, R12–R14 | Existing character/fusion, service, API and UI regressions; invalid evidence path test | PASS engineering |
| R8–R10 | Exactly 21 configurations; safety-first gates and all tie-break levels; actual no-winner freeze plus overwrite tests | PASS evaluation behavior; quality FAIL |
| R11 | Winner-construction unit test retains 21 summaries and full-report checksum; no real winner produced | Conditional failure path PASS; real winner NOT APPLICABLE |
| R15 | Raw samples, hardware/runtime, index counts and declared measurement protocol | Measurement PASS; both p95 budgets FAIL |
| R16–R20 | No final query/label/score work and no persistence promotion | Deferred/blocked; feature not approved |

Verification: 236 executable tests pass with one existing deprecation warning. Focused Ruff F/I,
isolated strict MyPy on `human_knowledge.py`/`human_knowledge_selection.py`, compilation, JavaScript
syntax, both default/PostgreSQL-profile Compose static configurations, source/projection/development/
v1 query/benchmark/report checks, fixture validation and `git diff --check` pass. A fresh canonical
fixture report in a temporary directory retains Recall@25/Top-1/MRR/precision 1.0, false-match rate
0, and coverage 0.8333; it is not a new independent accuracy claim. Container execution and SQL
runtime were not repeated. Whole-repository lint/type debt is unchanged, not silently waived.

Blocking findings: every configuration returns candidates for 10/20 unrelated controls and has
real p95 29.37–36.60 ms / synthetic p95 337.15–377.28 ms. See the
[AI evaluation](../../docs/evidence/ai-evals/human-knowledge-retrieval-development-v1.md).
Return to Phase 1: revise the identity-admission and bounded-comparison design under a new decision;
do not lower gates, expand the viewed grid, choose the closest result, or author final v2 questions.
