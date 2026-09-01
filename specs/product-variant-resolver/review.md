# Product Variant Resolver — Lite MVP QA Review

> Date: 2026-09-01  
> QA mode: `.codex/agents/qa.toml` MVP Mode  
> Scope: `specs/product-variant-resolver/mvp-brief.md` R1–R16  
> Verdict: **PASS WITH RISKS**

## Verdict summary

The dependency-light, offline fixture path is demonstrable and internally consistent. All 38
available unit, integration, API, UI, fixture, training, evaluation, and reporting tests passed;
Python compilation, fixture validation, report regeneration, report disclosure validation, and
Docker Compose static configuration also passed. Manual API spot checks produced all three decision
states, omitted debug data by default, bounded debug candidates, and failed closed for missing
catalog, PostgreSQL backend selection, and unavailable external model providers.

The focused re-verification also confirms the three requested corrections: series knowledge is
derived from the catalog and a conflicting series remains a soft conflict; RRF is the default
runtime ranker based on a traceable frozen-test comparison showing zero Top-1 gain from the local
heuristic reranker; and the report contains warmed in-process HTTP/ASGI `/resolve` samples with an
explicit statement that container/TCP latency was not measured.

This is not a full verification of every technology named in the MVP brief. PostgreSQL/pgvector
resolution adapters and pinned external embedding/cross-encoder models remain explicitly deferred.
The Docker daemon was not running, so no image build, container health check, migration, or live
PostgreSQL test was performed. The new HTTP measurement crosses the FastAPI middleware,
validation, dispatch, serialization, and response-header boundary through in-process TestClient,
but excludes a real socket, Docker, reverse proxy, and concurrency. These limitations are disclosed
in the README and generated report and must remain visible in any portfolio or repository claims.

## Requirement coverage

| Requirement | Result | Evidence / limitation |
|---|---|---|
| R1 Canonical resolution | PASS | Manual `POST /resolve` check returned `matched`, UUID/slug/product, and bounded confidence; benchmark matched cases passed. |
| R2 Ambiguity | PASS | Manual fixture check returned `ambiguous`, null identity, and machine-readable reason `confidence_below_match_threshold`. |
| R3 Unknown entity | PASS | Manual fixture check returned `no_match`, null identity, reason `no_candidate_above_threshold`. |
| R4 Default minimization | PASS | Default response keys exclude `debug`, candidates, ranks, scores, and timings. |
| R5 Explainability | PASS | Debug response contains extracted signals, bounded candidates, sparse/dense/structured/RRF/reranker fields, conflicts/matches, model versions, and all component timings. With the R11 default decision, reranker fields are present as null and the debug/health metadata explicitly says `disabled`; opt-in mode populates them. |
| R6 Syntax/knowledge boundary | PASS (fixture path) | Generic catalog ingestion is idempotent; catalog-derived color addition test passes; static review found no product-specific retrieval branch. Full PostgreSQL ingestion is deferred. |
| R7 Soft conflicts | PASS | Catalog-derived `series_hints` is implemented without a product-specific branch. Manual and integration checks show a target with the wrong catalog series remains in the top 25 and records `series` in `structured_conflicts`; year/color retention and collector-number logic remain intact. |
| R8 Reproducible split | PASS | 100 cases; `split_seed=240901`; version `fixture-v1`; 14 families occur in exactly one split; train/dev access guards pass; test labels are recorded as untouched by training. |
| R9 Retrieval gate | PASS | Fresh test evaluation: Recall@25 `1.0` on 12 matched test cases (gate `>=0.95`). |
| R10 Ranking gate | PASS | Fresh test evaluation: Top-1 `1.0`, hard-negative accuracy `1.0` (4/4). |
| R11 Reranker value | PASS (alternative) | On the same 12 matched frozen test cases, RRF Top-1 `1.0` and heuristic-v1 Top-1 `1.0`, absolute gain `0.0`. The versioned report therefore selects RRF and omits the heuristic from the default runtime, while retaining an explicit opt-in/ablation path. It states that no external cross-encoder was evaluated. |
| R12 Reliability gate | PASS | Precision `1.0`, false-match rate `0.0`, coverage `0.8333` on 21 synthetic fixture test cases. |
| R13 CPU smoke budget | PASS (limited scope) | Fresh warmed in-process HTTP/ASGI p95 `2.45 ms`, K=25, macOS arm64/Python 3.14.6 (gate `<=1500 ms`). It includes middleware, validation, dispatch, serialization, and headers. Report schema enforces the disclosure that Docker/container, TCP network, reverse proxy, and concurrent load were not measured. |
| R14 API validation | PASS | Blank, 501-code-point, unknown-field, and limit=26 requests return structured 422; malformed JSON returns 400; unsupported media type returns 415; no tracebacks exposed. |
| R15 Health/readiness | PASS WITH RISK | Missing catalog, PostgreSQL selection, external dense provider, and external reranker all produce health 503 and resolve 503 without identity. A simulated retriever failure fails closed, but live health transition after a runtime retriever failure is not verified. |
| R16 Quality gate | PASS (available suites) | 38/38 tests pass and versioned JSON/Markdown/SVG report generation and schema validation pass. Live browser, Docker, PostgreSQL/pgvector, and external-model paths were not run. |

## Checked items and reproducible evidence

Executed from the project repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
# Result: Ran 38 tests in 1.029s — OK

python3 -m compileall -q src tests scripts migrations
# Result: exit 0

python3 scripts/validate_fixture_data.py
# Result: exit 0; fixture manifest validated

PYTHONPATH=src python3 -m product_variant_resolver.evaluation
# Fresh result: Recall@25 1.0; Top-1 1.0; hard-negative 1.0;
# precision 1.0; coverage 0.8333; false-match rate 0.0; pipeline p95 3.29 ms

PYTHONPATH=src python3 scripts/train_calibration.py --output-directory /tmp/<qa-dir>
# Result: calibration and dev-selected policy generated; test_labels_accessed=false

PYTHONPATH=src python3 scripts/generate_evaluation_report.py --output-directory /tmp/<qa-dir>
# Result: versioned JSON, Markdown, and four SVG artifacts generated;
# fresh warmed in-process HTTP/ASGI p95 2.45 ms; schema/derivation audit passed

docker compose config --quiet
docker compose --profile postgres config --quiet
# Result: both exit 0 (static configuration only)
```

Additional audit results:

- Fixture: 120 products, 100 benchmark cases (`60 matched`, `20 ambiguous`, `20 no_match`),
  14 casting families, and 30 near-duplicate groups.
- Frozen catalog and benchmark SHA-256 values match `data/manifest.json`.
- Existing report passes its schema, metric-derivation, and disclosure validator.
- Report clearly says it covers 21 synthetic fixture test cases and does not establish production
  accuracy, marketplace coverage, or production readiness.
- R7 manual evidence: a catalog-provided wrong series was extracted as `series_hints`; the expected
  target remained retrievable and carried `structured_conflicts=["series"]`.
- R11 evidence: RRF and heuristic-v1 both have Top-1 `1.0` on the same 12 matched test cases. The
  checked-in and freshly generated reports record absolute gain `0.0`, `selected_default="rrf"`,
  `heuristic_reranker_runtime_enabled=false`, and `external_cross_encoder_evaluated=false`.
- R13 evidence: fresh report generation retained 21 warmed HTTP/ASGI samples after five excluded
  warm-up requests. p95 was `2.45 ms`; the validator rejects a changed/untraceable p95 or a false
  claim that container latency was measured.
- UI Node harness covers loading, matched success, ambiguous/empty-candidate, and API error states.
  Static and dynamic checks confirm backend-supplied markup remains text and `innerHTML`,
  `insertAdjacentHTML`, and `eval` are not used.
- Secret scan found only the documented local-only Compose PostgreSQL password; no API keys,
  private keys, or hardcoded production credentials were found.
- `python3 -m pytest` was unavailable because pytest is not installed in the host interpreter;
  the same unittest-compatible suite was run directly and passed.
- Package wheel build could not be verified offline because the host lacks setuptools and the uv
  cache has no `setuptools>=75`; `compileall` passed. No dependency was downloaded for QA.

## Findings

### Blocker

None for demonstrating the explicitly documented offline fixture path.

### Important

1. **PostgreSQL/pgvector is not a runtime resolver path.** Alembic schema and bound SQL constants
   exist, but `PostgresRetrieverAdapter.execute_ranked` is unimplemented and selecting
   `PVR_BACKEND=postgres` intentionally makes readiness fail. The Compose profile can reserve and
   migrate a database only; it does not exercise PostgreSQL FTS or exact pgvector retrieval.
2. **External neural models are not integrated.** The verified dense provider is `hashing-v1` and
   reranker is `heuristic-v1`. `config/models.example.json` still contains replacement placeholders;
   selecting an external provider fails closed. Do not describe the reported results as a
   sentence-transformer or cross-encoder benchmark.
3. **Docker runtime is unverified.** `docker compose config` passes, but the daemon socket was absent.
   Image build, Python 3.12 container execution, readiness probe, read-only filesystem behavior,
   Alembic migration, and pgvector extension creation remain untested.

### Later

1. Run the suite on Python 3.12 as pinned by the project; current host verification used Python
   3.14.6.
2. Resolve the Starlette `TestClient` deprecation warning (`httpx` versus `httpx2`) before a future
   dependency upgrade turns it into a failure.
3. Add an actual browser smoke test if UI behavior beyond the Node DOM harness becomes release
   critical.
4. Add readiness-state coverage for a retriever/model that fails after startup, not only missing or
   unsupported dependencies at app creation.

## Recommended next task

The requested R7, R11, and R13 corrections are QA-closed for the Lite offline fixture scope. The
next highest-value task is to run the existing stack in Docker on Python 3.12 and preserve the
container/TCP limitation until that evidence exists. PostgreSQL/pgvector and external neural model
work can remain deferred only if the README, reports, and repository description continue to say so
explicitly; otherwise implement and integration-test those adapters before claiming the original
technology scope complete.
