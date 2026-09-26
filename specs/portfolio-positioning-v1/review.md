# Portfolio positioning and README restructure v1 — QA Review

Date: 2026-09-26. Mode: Lite / Lean Industrial. Reviewer: `qa`.

## Verdict

**PASS** for PP-R1–PP-R16 and the documentation-only PP-T5 acceptance boundary.

The README now functions as a scoped portfolio landing page, the portfolio guide provides the
required interview material, all checked repository-relative links resolve, the displayed fixture
and neural-comparison values match their checked-in evidence, and the working diff contains no
product/runtime changes. The full product test suite was not rerun because this milestone changes
documentation only; instead, QA used link, metric, terminology, file-scope, whitespace, and Python
compile checks proportional to the change risk.

## Checked items and evidence

- README H2 order is: confidence-aware entity-resolution hero; Problem; Architecture; Key
  engineering decisions; Measured evaluation; Neural comparison; Limitations; Run locally; Deep
  evidence.
- Local Markdown target scan checked 54 README links and 12 Portfolio Guide links; missing targets:
  `0`. README quick-link anchors were also matched to their headings.
- `data/benchmark.json` contains 100 cases, `data/catalog.json` contains 120 products, and the
  fixture report records 21 Test cases with 12 matched targets. README counts and all displayed raw
  denominators match `reports/fixture-v1/evaluation-fixture-v1-test.md` and its adjacent JSON.
- The neural table matches `reports/neural-reranker-comparison-v1/comparison.md`: all arms Top-1
  `12/12`; resolver p95 `1.398 ms`, `89.164 ms`, and `89.583 ms`; `winner: null`; RRF remains the
  runtime default.
- `docs/PORTFOLIO-GUIDE.md` contains exactly three bullets under Current-evidence resume bullets,
  exactly one 60–90 second pitch section, claim guardrails, and one explicitly future-only metric
  template.
- Terminology scan found `hashing-v1` consistently described as deterministic/non-neural; Dual RAG
  appears below the headline as an authority boundary; neural models are shadow-only; production
  and marketplace claims occur only as explicit limitations or prohibited claims.
- The Deep evidence table retains destinations for core QA, neural comparison, human-labeled
  import/alignment, Human Knowledge, negative experiments, Wiki adjudication, owner-supplied staging,
  PostgreSQL/storage, runtime/Docker validation, portfolio positioning, and engineering chronology.
- Working-tree scope before this review was limited to `README.md`, `docs/PROJECT-LOG.md`,
  `docs/PORTFOLIO-GUIDE.md`, and `specs/portfolio-positioning-v1/*`; there are no changes under
  `src/`, `ui/`, `data/`, `migrations/`, dependency manifests, model artifacts, or runtime config.
- `git diff --check`: PASS.
- `.venv/bin/python -m compileall -q src`: PASS. This confirms the documentation work did not
  disturb Python compilation without pretending to revalidate unchanged runtime behavior.

## Requirement coverage

| Requirement | QA check and evidence | Result |
|---|---|---|
| PP-R1 | README hero says “Confidence-Aware Product Entity Resolution”; RAG, LLM, and vector database are not the primary headline. | PASS |
| PP-R2 | Problem precedes setup, explains noisy titles, near-identical variants, abstention risk, and names `matched`, `ambiguous`, `no_match`. | PASS |
| PP-R3 | Architecture shows signal extraction, sparse/similarity/structured retrieval, RRF, calibration, policy, soft conflicts, and canonical-only UUID authority. | PASS |
| PP-R4 | Human Knowledge is a separate explanation/review branch and cannot create, promote, or replace canonical identity; README says no LLM generates the answer. | PASS |
| PP-R5 | README and guide explicitly state that `hashing-v1` is deterministic, hashing-based, and not a learned neural embedding model. | PASS |
| PP-R6 | MiniLM pointwise/listwise are described as isolated shadow arms over the same frozen Top-25 pools; neither is active in FastAPI; RRF is default. | PASS |
| PP-R7 | README preserves `12/12` for all arms, p95 `1.398/89.164/89.583 ms`, `winner: null`, no ranking gain, saturation, and the non-universal limitation. | PASS |
| PP-R8 | README discloses 100 benchmark cases, 120 catalog products, 21 Test cases, and 12 matched targets; perfect metrics have raw denominators and fixture scope. | PASS |
| PP-R9 | Dedicated Limitations names fixture size, saturation, scale/concurrency limits, non-neural default representation, and absent real-marketplace generality. | PASS |
| PP-R10 | No evidence artifact was removed in the diff; every condensed audit category has at least one valid Deep evidence destination. | PASS |
| PP-R11 | README section order matches the required portfolio reading path and keeps audit chronology out of the primary narrative. | PASS |
| PP-R12 | Portfolio Guide has exactly three current-evidence bullets and one pitch; future metrics are clearly labeled unmeasured/future-only. | PASS |
| PP-R13 | README retains offline install, Uvicorn start, `/resolve`, `/health`, debug behavior, and links to deeper PostgreSQL/storage evidence. | PASS |
| PP-R14 | Project Log records the communication problem, changed files/sections, entity-resolution headline rationale, Dual-RAG detail, hashing wording, and link-not-delete decision. | PASS |
| PP-R15 | Diff is documentation/spec only; no product code, schema, ranking, calibration, data, migration, dependency, model, or fixture change exists. | PASS |
| PP-R16 | All 66 checked local links resolve; metrics/latencies are consistent; terminology and unsupported-claim scans pass; no product-code diff; `git diff --check` passes. | PASS |

## Findings

### Blocker

None.

### Important

None for this milestone.

### Later / repository maintenance

- A diagnostic whole-repository `.venv/bin/python -m mypy src` run reports 51 existing findings in
  18 unchanged source files, including missing optional dependency stubs and long-standing strict
  typing debt. This is not caused by, and cannot be corrected within, PP-R15's documentation-only
  boundary. Python compile validation passes. Track the repository-wide type debt as a separate
  maintenance task if a clean global MyPy gate is desired.
- PP-T1–PP-T5 task-status closure was pending during the initial review and is confirmed complete in
  the closure recheck below.

## Recommended next task

Commit the documentation-only diff. The next product-facing improvement should be a separate spec
for a representative hard benchmark rather than another README or model-complexity change.

## Closure recheck

Rechecked after milestone closeout on 2026-09-26. **Verdict remains PASS.**

- `tasks.md` now has Status `COMPLETE`, and PP-T1, PP-T2, PP-T3, PP-T4, and PP-T5 are all checked.
- The top Project Log entry now covers the complete PP-T1–PP-T5 milestone: the README landing-page
  rewrite, Portfolio Guide, requirements/design/tasks/review artifacts, PP-R1–PP-R16 QA result,
  documentation-only validation, retained limitations, and the representative hard-benchmark next
  step.
- The Project Log still satisfies PP-R14 by recording the communication problem, exact documentation
  surfaces, entity-resolution headline rationale, Dual-RAG authority-boundary role, `hashing-v1`
  terminology, and the decision to link rather than delete deep evidence.
- The Project Log and final working diff still satisfy PP-R15: no product code, API, data, model,
  dependency, ranking, calibration, migration, fixture, or runtime configuration changed.
- Allowed-file scope is limited to `README.md`, `docs/PROJECT-LOG.md`,
  `docs/PORTFOLIO-GUIDE.md`, and `specs/portfolio-positioning-v1/*`.
- Final `git diff --check`: PASS.
