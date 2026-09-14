# IBR-T3 — Frozen v4 development selection and cost evidence

Date: 2026-09-14. Mode: Lite, no subagents. Engineering checkpoint and development gates: PASS.
Independent final accuracy, runtime closure, T49/real expansion/default deployment: NOT APPROVED.

## Frozen artifacts and provenance

- Protocol SHA-256: `31802be99f02698423c4526bbd8752e6f517fcbef8ca8080926d019f55083fde`.
- Manifest SHA-256: `b7634f7f3d52277c4ee4d92489b656fcf1a6c446d56085c5affb7cb7a12c6ea7`.
- [Selection JSON](../../reports/human-knowledge-identity-development-v1/selection.json), SHA-256:
  `f52f85f775806d43a57c11e5fa9f7f965da980f54cc58a814d727fdfe7876f42`.
- [Readable report](../../reports/human-knowledge-identity-development-v1/selection.md).
- [Selected artifact](../../config/human-knowledge-retrieval-v4.json), version
  `human-knowledge-retrieval-v4-dev-f52f85f77580`, SHA-256
  `82c94a2629da6936bec3e4a2983e67c70d69e94cb94a9817375f891d59b1ae6b`.

Protocol was committed at `aed899c`; oracle/wiring implementation at `18aa562`, before real v4
selection output. New evaluator and runtime raw-evidence validation were finalized/tested before
this run and are checksum-bound in its JSON. Runtime core/policy/limits/hashing/normalizer and all
protected v3 sources/data/reports were unchanged. Old 199-case development is deliberately reused
and already viewed, not a fresh blind split. No v1 final input was read by evaluation/report checks.
Historical v1 reproduction is separately a regression, not selection input.

## Complete run and deterministic winner

Exactly seven floors × three weights: **21 configurations**, all passing every development gate.
All **4,179 real outputs**, **2,520 scale outputs**, candidates, work, expected identities, raw samples,
rejections, subtype totals, runtime/corpus/source checksums are retained. Expected identities are
attached only after the result is complete; no denominator or positive abstention is excluded.

Predeclared MRR → Recall@1 → higher floor → lower character weight selects **0.50 / 1.0**:

| Gate / evidence | Selected result | Required |
|---|---:|---:|
| Positive Recall@5 | 168/168 = 1.0000 | ≥0.90 |
| Positive Recall@1 | 165/168 = 0.9821 | Tie-break metric |
| MRR@5 | 166.5/168 = 0.9911 | Tie-break metric |
| Each edit/spacing/abbreviation/context style | 42/42 | ≥0.85 each |
| Merge-control Recall@5 | 4/4 | 1.0 |
| Forbidden family candidates | 0 | 0 |
| Unrelated nonempty | 0/20 | 0 |
| Real 142 p50 / p95 | 0.21 / 2.07 ms | p95 ≤25 ms |
| Synthetic 3,000 aggregate p95 | 45.14 ms | ≤150 ms |
| Exact / edited / contextual scale targets | 60/60; 20/20; 20/20 | 60; ≥17; 20 |

Floors ≤0.50 retrieve all 168 positives. Floor 0.55 has 166/168 and misses two abbreviation/edit
questions for one family; its quality still passes, but it does not win the predeclared ranking
tie-break. No grid/policy/limit/rank rule was adjusted after viewing this. Across all settings real
p95 is 2.02–3.00 ms and scale aggregate p95 44.12–62.17 ms; no result is discarded.

## Work and measurement boundary

Host: Darwin 24.6.0, Python 3.12.13, arm64, 10 logical CPUs, processor reported `arm`; the sandbox
CPU-brand lookup did not supply a more specific name. One retrieval process, K=5, three warm-ups per
corpus/setting, `perf_counter_ns`, nearest-rank percentiles, non-isolated host. Full test verification
briefly overlapped the first configuration's startup/early measurement; no contaminated-looking
sample/configuration was removed or rerun. This is disclosed diagnostic cost, not a dedicated-host,
production, concurrent-load or statistically controlled causal performance result.

All 199 real / 120 scale raw retrieval-with-work samples decide the gates. Startup/index/vector build,
signal extraction, serialization, HTTP, SQL, network and concurrent request load are excluded. The
selected scale original-20 / exact-60 / edited-20 / contextual-20 p95 is respectively
**61.22 / 0.87 / 1.49 / 12.24 ms**. All-setting original-20 p95 is **58.93–118.85 ms**. The aggregate
contains many easier exact probes, so use the original-20 subgroup—not aggregate 120—as the more
comparable old-v3 diagnostic workload. Original v3 original-20 p95 remains 337.15–377.28 ms in its
unchanged report, under the same Python/arm64/10-CPU description but a different non-isolated run
and score/index representation. Observed differences are not proof of an isolated optimization effect.

Selected real index: 142 docs / 284 forms / 8,051 form-gram posting entries; scale: 3,000 / 12,000 /
257,640. These are a new form-level definition, not directly comparable old document-posting memory.
Real max query forms / posting visits / scored forms / dense union: **90 / 18,707 / 267 / 7**.
Scale maxima: **60 / 434,052 / 6,676 / 25**. Both are within caps; no posting/window/query-budget
abort. Real has ten noise-only abstentions on generic negatives; they remain in the 199-case totals.
All positive synthetic probes succeed, so this is not a fast empty-output trick. However synthetic
casting cores retain digits; Scale→Scxle edits a removed wrapper, not true retained-name spelling.

## Engineering and publication safety

18 new evaluator/publication/genuine-replay/runtime tests; focused T3 plus artifact checks: **48 pass**.
Full repository: **329 pass**, no skips, one prior Starlette/AnyIO warning. Focused Ruff F/I, isolated
strict MyPy evaluator/validator, Python compilation, Node syntax, whitespace, default/PostgreSQL
profile Compose/context checks pass. Protocol, old dev, v3 JSON/Markdown and v1 JSON/Markdown checks
remain valid. Raw report and readable report check without retrieval.

Orchestration fixtures deliberately use empty fake retrieval (not a model winner) to prove 21 grids,
6 warm-ups/configuration, full denominators, no-v1 reads and scale correctness failure regardless of
cheap latency. Real-report tampering tests reject missing/altered grid/cases/samples/subgroups/work/
targets/metrics/winner/runtime/source. Exclusive temporary-file publication cannot overwrite existing
outputs, and invalid artifact bytes never become a final path. Genuine selected-artifact/API loading,
health/debug SHA and canonical equality pass; default v2 remains active.

Generated public evidence inherits temporary-file 0600 host modes. Docker now grants copied public
catalog/config/report/builder read/traversal permission for non-root `pvr`, preserving checksum bytes
and no write permission. Static packaging passed; no new image build/run was executed here. That
fresh container-runtime verification remains T5 closure work, not implied by genuine in-process API.

```bash
PYTHONPATH=src .venv/bin/python -m product_variant_resolver.human_knowledge_identity_selection --run
PYTHONPATH=src .venv/bin/python scripts/generate_human_knowledge_identity_selection_report.py
PYTHONPATH=src .venv/bin/python scripts/freeze_human_knowledge_v4.py
PYTHONPATH=src .venv/bin/python -m product_variant_resolver.human_knowledge_identity_selection --check
PYTHONPATH=src .venv/bin/python scripts/generate_human_knowledge_identity_selection_report.py --check
PYTHONPATH=src .venv/bin/pytest -o addopts='' -q
```

`--run` refuses an existing report. Check frozen results instead of resampling/tuning. Default artifact
path is committable `config/`, not ignored model-cache/artifacts. Commit winner/code/report/artifact
before T4. Next: author 105 new output-blind final questions, reject reused questions and obtain owner
approval before labels/retrieval. No new final questions, labels, final score, actual SQL growth,
default switch or whole-feature/T49 release occurred in T3.
