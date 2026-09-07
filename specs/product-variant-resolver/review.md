# Product Variant Resolver — Lite MVP QA Review

> Date: 2026-09-01  
> Last focused update: 2026-09-07 (T10 PostgreSQL exact dense retrieval)
> QA mode: `.codex/agents/qa.toml` MVP Mode  
> Scope: `specs/product-variant-resolver/mvp-brief.md` R1–R20
> Verdict: **PASS WITH RISKS**

## Verdict summary

The dependency-light, offline fixture path is demonstrable and internally consistent. The original
38-test QA suite passed, and the later fresh constrained Python 3.12 host suite passed 41/41;
Python compilation, fixture validation, report regeneration, report disclosure validation, and
Docker Compose static configuration also passed. Manual API spot checks produced all three decision
states, omitted debug data by default, bounded debug candidates, and failed closed for missing
catalog and unavailable external model providers. T09 later verified the opt-in PostgreSQL sparse
backend and its own fail-closed cases.

The focused re-verification also confirms the three requested corrections: series knowledge is
derived from the catalog and a conflicting series remains a soft conflict; RRF is the default
runtime ranker based on a traceable frozen-test comparison showing zero Top-1 gain from the local
heuristic reranker; and the report contains warmed in-process HTTP/ASGI `/resolve` samples with an
explicit statement that container/TCP latency was not measured.

The T26–T28 data additions passed the current host suite **57/57**, including four corpus tests,
five alignment tests, and seven human-backed catalog tests. The fixture validator now includes the
auxiliary dataset, alignment, and draft-catalog checksums plus label/status/identity invariants;
Python compilation and `git diff --check` also pass. These tests validate the imported artifacts
and their boundaries, not canonical resolution accuracy on the newly imported names.

T29 executes an independent human-knowledge retrieval stage on every resolution request while
preserving the canonical catalog as the only final-identity authority. The current host suite passes
**64/64**. The reviewed BMW query ranks the expected provisional variant first but still returns
`no_match` and a null canonical UUID; missing or review-bypassing human catalogs fail closed; debug
results are bounded and omitted by default. This proves the dual-source execution and safety
boundary, not accuracy on unseen real-world queries.

T07 is now runtime-verified against an isolated PostgreSQL 16/pgvector database. The first import
created 120 products, 240 aliases, 120 identifiers, 120 provenance rows, 120 sparse-search documents,
and one metadata row. Repeating the import preserved every row exactly. A mid-import identity
collision and a 119-of-120 incomplete snapshot both rolled back without changing the accepted
catalog. That milestone closed persistence but did not, by itself, prove PostgreSQL retrieval.

T09 now connects the canonical sparse-retrieval boundary to PostgreSQL full-text search. An
isolated PostgreSQL 16.14 run recovered all 12 matched frozen-test targets within Top-25, returned
an exact identifier at Top-1, used the existing GIN index under a forced index-compatible plan, and
kept an injection-shaped title in bound parameters. The PostgreSQL-backed API passed both
in-process and real HTTP resolution, while a corrupted catalog checksum failed readiness with 503.
The host suite at that milestone passed **71/71**.

T10 now materializes the versioned 192-dimensional `hashing-v1` catalog vectors and performs exact
cosine-distance retrieval with pgvector. The isolated PostgreSQL 16.14 run stored 120/120 vectors,
proved identical repeated materialization, recovered a catalog alias plus all 12 matched test
targets within Top-25, and rejected an intentionally missing row at readiness. A real HTTP request
reported both PostgreSQL candidate sources ready and kept the expected Nomad identity first in
sparse, dense, structured, and fused ranks. The final host suite passes **77/77**. This verifies the
database vector lifecycle, not a neural embedding model.

An independent Docker runtime milestone now verifies the existing
`product-variant-resolver:lite` image on Docker Desktop 29.5.3/aarch64: Python 3.12.14, non-root
user `pvr` (UID 100), read-only root filesystem, writable tmpfs only, loopback-only published port,
healthy readiness, UI assets, all three decision states, and missing-catalog fail-closed behavior.
The checked-in host-to-container latency artifact is arithmetically traceable: 50 sequential raw
samples after 10 warm-ups produce nearest-rank p95 `4.721208 ms`.

Focused re-verification closed the prior runtime reporting dependency finding. `httpx2>=2,<3` is a
reasonable runtime dependency because the shipped `pvr-report` CLI directly uses FastAPI
TestClient. The selective Python 3.12 constraints freeze the compatibility-sensitive web stack,
remove legacy `httpx`, and hold AnyIO at 4.14.0 to avoid the alias warning exposed by AnyIO 4.15.1
with Starlette 1.6. A no-cache rebuild resolved the complete selected set and, in the rebuilt
read-only image, `pvr-report` generated JSON, Markdown, and four SVGs successfully.

T04 is now QA-closed as **PASS**. An isolated PostgreSQL 16/pgvector run completed the empty →
upgrade `0001` → downgrade `base` → upgrade `0001` cycle and compared both upgraded schemas. The
follow-up runner now proves index table/name/method/ordered columns, complete foreign-key
source/target/delete behavior, and the full normalized release-year check expression; Alembic's
script location is absolute. A sentinel application table caused the runner to refuse execution,
closing the prior safety-check concern. T07 separately verifies fixture ingestion, T09 verifies the
PostgreSQL FTS query adapter, and T10 verifies versioned exact-vector query execution.

This is not a full verification of every technology named in the MVP brief. PostgreSQL sparse and
exact dense resolution are verified with deterministic `hashing-v1`, while external neural
embedding/cross-encoder models remain explicitly deferred.
The Docker latency evidence is from one local arm64 machine over loopback with concurrency 1; it
does not cover TLS, a reverse proxy, a remote network, concurrent load, or PostgreSQL. The committed
constraints are selective rather than a complete transitive lock; PostgreSQL extras and other
unlisted indirect/build dependencies can still resolve differently. These limitations must remain
visible in any portfolio or repository claims.

## Requirement coverage

| Requirement | Result | Evidence / limitation |
|---|---|---|
| R1 Canonical resolution | PASS | Manual `POST /resolve` check returned `matched`, UUID/slug/product, and bounded confidence; benchmark matched cases passed. |
| R2 Ambiguity | PASS | Manual fixture check returned `ambiguous`, null identity, and machine-readable reason `confidence_below_match_threshold`. |
| R3 Unknown entity | PASS | Manual fixture check returned `no_match`, null identity, reason `no_candidate_above_threshold`. |
| R4 Default minimization | PASS | Default response keys exclude `debug`, candidates, ranks, scores, and timings. |
| R5 Explainability | PASS | Debug response contains extracted signals, bounded candidates, sparse/dense/structured/RRF/reranker fields, conflicts/matches, model versions, and all component timings. It reports selected sparse and dense implementations, including PostgreSQL exact-dense artifact version. With the R11 default decision, reranker fields are null and metadata says `disabled`; opt-in mode populates them. |
| R6 Syntax/knowledge boundary | PASS (fixture path) | Generic catalog ingestion is idempotent and PostgreSQL-runtime verified. Structured alias/identifier source data is preserved, the full searchable catalog is checksummed, and catalog-derived color addition needs no product-specific branch. T09 moves only canonical sparse retrieval into PostgreSQL; the independent human-knowledge source cannot issue canonical identity. External Wiki ingestion/review remains deferred. |
| R7 Soft conflicts | PASS | Catalog-derived `series_hints` is implemented without a product-specific branch. Manual and integration checks show a target with the wrong catalog series remains in the top 25 and records `series` in `structured_conflicts`; year/color retention and collector-number logic remain intact. |
| R8 Reproducible split | PASS | 100 cases; `split_seed=240901`; version `fixture-v1`; 14 families occur in exactly one split; train/dev access guards pass; test labels are recorded as untouched by training. |
| R9 Retrieval gate | PASS | Fresh offline evaluation, PostgreSQL FTS, and exact pgvector each achieved Recall@25 `1.0` on the same 12 matched test cases (gate `>=0.95`). |
| R10 Ranking gate | PASS | Fresh test evaluation: Top-1 `1.0`, hard-negative accuracy `1.0` (4/4). |
| R11 Reranker value | PASS (alternative) | On the same 12 matched frozen test cases, RRF Top-1 `1.0` and heuristic-v1 Top-1 `1.0`, absolute gain `0.0`. The versioned report therefore selects RRF and omits the heuristic from the default runtime, while retaining an explicit opt-in/ablation path. It states that no external cross-encoder was evaluated. |
| R12 Reliability gate | PASS | Precision `1.0`, false-match rate `0.0`, coverage `0.8333` on 21 synthetic fixture test cases. |
| R13 CPU smoke budget | PASS (limited scope) | Checked-in host-to-Docker loopback evidence has 50 sequential samples, 10 excluded warm-ups, K=25, and nearest-rank p95 `4.721208 ms` (gate `<=1500 ms`). That measurement remains offline-only. PostgreSQL exact retrieval passed sequential functionality checks, but database latency, concurrency, TLS/proxy, and remote networking were not measured. |
| R14 API validation | PASS | Blank, 501-code-point, unknown-field, and limit=26 requests return structured 422; malformed JSON returns 400; unsupported media type returns 415; no tracebacks exposed. |
| R15 Health/readiness | PASS WITH RISK | Missing catalogs and unavailable external providers fail closed. PostgreSQL startup verifies server/catalog state plus dense metadata and every expected UUID/version/checksum; catalog checksum corruption or one missing vector produces health 503, and retrieval-time database failure maps to 503. Health remains a startup snapshot, so post-startup loss is detected on retrieval. |
| R16 Quality gate | PASS | The latest host suite passes 77/77; fixture validation, Python compilation, default/PostgreSQL Compose configuration, and `git diff --check` pass. T04 migration, T07 ingestion, T09 sparse, and T10 exact dense retrieval passed isolated PostgreSQL 16/pgvector verification. Offline remains the default; PostgreSQL canonical sparse+dense is opt-in. |
| R17 Human-label provenance | PASS | `human-labeled-real-noisy-v1` contains 101 confirmed human labels, including 91 initial-name/human-name pairs and 10 explicit `no_candidate` failures. Four source rows marked excluded were not imported. The frozen manifest records source and dataset checksums, and the corpus declares that it is excluded from canonical-resolution accuracy, calibration training, and threshold selection until catalog IDs are assigned. |
| R18 Conservative catalog alignment | PASS | The deterministic alignment covers all 101 reviewed records and freezes the human dataset, catalog, and output checksums. It reports 0 canonical mappings, 2 exact brand/casting family-only matches, and 99 unmapped records. Every unresolved record retains null UUID/slug; fuzzy matching is disabled. |
| R19 Human-backed catalog draft | PASS | All 101 confirmed labels are preserved in 97 deterministic casting entities and 100 provisional variants. One exact structured duplicate merges while keeping both cases and aliases. Checksums and unique IDs validate, and every provisional variant remains `needs_canonical_review` and excluded from canonical responses and calibration. |
| R20 Dual-source retrieval boundary | PASS (Lite scope) | Every request executes canonical retrieval plus an independent human-knowledge sparse/dense/RRF retrieval stage. Only canonical candidates enter ranking, policy, and final identity. A reviewed BMW query returns the expected provisional suggestion in bounded debug output while the canonical result stays `no_match`/null; unknown text returns no human suggestion; missing or review-bypassing human data fails closed; default responses omit both debug candidate sets. |

## Checked items and reproducible evidence

Executed from the project repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
# Latest focused rerun: Ran 38 tests in 0.928s — OK

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

Docker/Python 3.12 runtime milestone:

```text
Image: product-variant-resolver:lite
Latest rebuilt image ID: sha256:e67d64e95abab329c901bdb5946f86962a09dc7217e2048a3b1c0568ec8b9d75
Docker server / architecture: 29.5.3 / aarch64
Container Python: 3.12.14
Runtime user: uid=100(pvr), gid=101(pvr)
ReadonlyRootfs: true
Published port: 127.0.0.1:8000 -> 8000/tcp
Compose state: healthy
```

- `/app` is not writable; `/tmp` tmpfs is writable.
- Container source/migration compile passed using `/tmp` as the bytecode cache.
- The prior runtime milestone's read-only mounted Python 3.12 runs passed 26 tests: 10 unit, 7 integration,
  4 evaluation metrics, and 5 fixture tests.
- That milestone's direct container evaluation remained green: Recall@25 `1.0`, Top-1 `1.0`, hard-negative
  accuracy `1.0`, precision `1.0`, coverage `0.8333`, false-match rate `0.0`; container pipeline
  p95 was `1.380833 ms` on this run.
- Real host-to-container HTTP returned health 200/ready; `/`, `/app.js`, and `/styles.css` returned
  200; `matched`, `ambiguous`, and `no_match` fixtures returned their expected states; the default
  response omitted debug fields and supplied `x-request-id`.
- A dedicated missing-catalog container returned health and resolve 503 without an identity and was
  removed immediately after the check.
- Compose logs contained normal startup, health, UI, and resolve access entries with no traceback or
  application error.
- `reports/runtime-validation/docker-python312-http-latency.json` has the exact expected v1 keys,
  50 finite non-negative raw samples, and matching min/median/mean/max. Sorting the samples and
  applying `ceil(0.95 * 50) - 1` reproduces p95 `4.721208 ms` exactly.
- Runtime latency evidence is single-machine arm64, loopback, sequential, concurrency 1, and offline
  memory only. It excludes TLS, proxying, remote networking, concurrent load, and PostgreSQL.

Focused dependency-contract and reporting re-verification:

- `pyproject.toml` now declares `httpx2>=2,<3` in runtime dependencies. This placement is justified
  because `pvr-report` is installed in the runtime image and calls FastAPI TestClient directly.
- `constraints/python312.txt` selectively fixes FastAPI `0.141.1`, Starlette `1.6.0`, httpx2
  `2.12.0`, httpcore2 `2.12.0`, AnyIO `4.14.0`, Pydantic `2.13.5`, and Uvicorn `0.52.4`.
  Legacy `httpx` was removed from the dev extra. A no-cache Docker build succeeded with this exact
  set; `python -W error` imported TestClient without warning and confirmed legacy `httpx` absent.
- Inside the rebuilt read-only/non-root container, `pvr-report --output-directory
  /tmp/qa-runtime-report` generated exactly: one JSON, one Markdown, `retrieval-ablation.svg`,
  `reranker-comparison.svg`, `precision-coverage.svg`, and `latency.svg`.
- The generated JSON passed `validate_report_payload`, used schema
  `pvr-evaluation-report-v2`, retained 21 HTTP samples, and preserved the exact 21-case synthetic
  non-production disclosure plus `container.measured=false`.
- Generated Markdown retained the non-production statement, no-external-cross-encoder statement,
  and container-latency-not-measured statement. All four SVGs contain `<svg>` and `<title>`.
- Rebuilt-image mounted tests: all 39 tests not requiring Node passed across backend, API,
  evaluation, reporting, integration, unit, and fixture scopes. The attempted full 41-test
  selection errored only at the UI controller test because the runtime image has no Node; the
  fresh constrained host environment is the 41/41 UI-inclusive evidence.
- Compose became healthy; inspection showed `User=pvr` and `ReadonlyRootfs=true`. Live health and
  three-state HTTP checks passed, and `ambiguous`/`no_match` returned no identity.
- The selective constraints are not a complete transitive lock. PostgreSQL extras and unlisted
  transitive/build dependencies remain range-resolved.

T04 PostgreSQL/pgvector migration verification:

- The existing `0001` migration required no schema change. In isolated Compose project `pvr-t04`
  on host port `55432`, PostgreSQL 16/pgvector passed empty → upgrade `0001` → downgrade `base` →
  upgrade `0001`; the first and second upgraded snapshots matched and final revision was `0001`.
- The strengthened runner verifies all seven application tables, primary/unique constraints, the
  complete normalized release-year expression, every required foreign key from its source column
  to `product_variant.canonical_uuid` with `ON DELETE CASCADE`, and each required index by table,
  name, method, ordered columns, and column order. It also verifies `tsvector`, `vector(192)`, and
  the installed `vector` extension. Its absolute Alembic `script_location` removes dependence on
  the caller's current directory.
- A sentinel application table present before invocation caused the runner to abort before any
  downgrade, closing the destructive-use safety finding. The guard checks existing application
  tables only; it does not inventory views, functions, custom types, or every possible schema
  object, so the runner remains restricted to a disposable database.
- The isolated container, network, and volume were removed after the checks. The responsible run
  also reported the host suite **41/41 PASS**, runner/migration Python compilation **PASS**, and
  `git diff --check` **PASS**. CI does not yet start PostgreSQL and execute this cycle automatically,
  and extension creation may require database-administrator permission.

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
- The host interpreter still cannot build a standalone wheel offline because it lacks setuptools
  and the uv cache has no `setuptools>=75`; however, the no-cache Docker build downloaded its
  declared dependencies and successfully built and installed the project wheel.

## Findings

### Blocker

None for demonstrating the explicitly documented offline fixture path.

### Important

1. **The PostgreSQL vector path uses a deterministic lexical baseline, not a neural model.** T10
   verifies materialization, version/readiness checks, and exact pgvector execution with
   `hashing-v1`. Its positive alias/fixture results must not be described as sentence-transformer
   semantic quality, and database latency at the planned 3,000-row scale is not measured.
2. **External neural models are not integrated.** The verified dense provider is `hashing-v1` and
   reranker is `heuristic-v1`. `config/models.example.json` still contains replacement placeholders;
   selecting an external provider fails closed. Do not describe the reported results as a
   sentence-transformer or cross-encoder benchmark.
3. **Dependency constraints are selective, not a complete lock.** The compatibility-sensitive
   FastAPI/Starlette/TestClient/AnyIO/Pydantic/Uvicorn set is constrained and container-verified,
   with legacy `httpx` removed. PostgreSQL extras and unlisted transitive/build dependencies remain
   range-resolved and require a broader lock/reverification before a production database release.

### Later

1. Add an actual browser smoke test if UI behavior beyond the Node DOM harness becomes release
   critical.
2. Add readiness-state coverage for a retriever/model that fails after startup, not only missing or
   unsupported dependencies at app creation.

## Recommended next task

The requested R7, R11, R13, Docker/Python 3.12 runtime, runtime reporting, selective dependency-
constraint, T04/T07/T09/T10 database milestones, and T26–T29 human-data/Dual-RAG milestones are
QA-closed for their stated Lite scope. The next highest-value database work is expanding the
reviewable catalog toward 3,000 variants and measuring exact pgvector quality and latency.
The next human-knowledge evaluation task remains an independently written, casting-grouped holdout
set; until that evidence exists, the human source stays debug-only. A complete dependency-lock
review, active post-startup database health polling, external neural models, and a justified T14
reranker remain deferred until held-out evidence supports them.
