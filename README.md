# Product Variant Resolver

A Lite/MVP, offline-first resolver that maps noisy Hot Wheels marketplace titles to a canonical
fixture product—or abstains with `ambiguous` / `no_match`. The verified default is deliberately
dependency-light: catalog-derived signals, token sparse retrieval, deterministic `hashing-v1`
dense retrieval, structured soft conflicts, RRF, logistic confidence, and abstention behind
FastAPI.

This is a portfolio-quality fixture validation, not evidence of production accuracy or marketplace
coverage.

## Architecture

```text
Debug UI / API client
        |
 FastAPI: /resolve, /health
        |
 generic signal extraction
        |
 sparse + hashing dense + structured candidates
        |
 RRF fusion (default)
        |
 optional heuristic-v1 reranker (ablation only)
        |
 calibration + decision policy
        |
 matched | ambiguous | no_match
```

Product knowledge—aliases, colors, series, identifiers, and variant attributes—lives in the
catalog. Conflicting structured signals remain soft ranking evidence instead of removing a
candidate. RRF stays on the default runtime path because the local heuristic reranker added `0.0`
absolute Top-1 accuracy on the frozen test; enable it only for an explicit experiment with
`PVR_RERANKER_ENABLED=true`. No external cross-encoder was evaluated.

## Start the offline path

The project targets Python 3.12. Final host QA ran on Python 3.14.6, so Python 3.12 runtime evidence
is still pending. QA exercised the source checkout directly; the editable package build was not
verified offline because the required setuptools artifact was unavailable on that host.

```bash
python -m pip install -e '.[dev]'
PYTHONPATH=src uvicorn product_variant_resolver.api:app --reload
```

Open `http://127.0.0.1:8000/` for the same-origin debug UI, or call the API:

```bash
curl --fail --json '{"title":"2022 Chevy Nomad Red #101","debug":true}' \
  http://127.0.0.1:8000/resolve
curl --fail http://127.0.0.1:8000/health
```

The normal response omits candidates, internal ranks/scores, and timings. `debug=true` exposes a
bounded explanation payload. UI values are rendered as text, and resolution logs omit raw titles.

## Verify and reproduce the fixture report

```bash
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v
python scripts/validate_fixture_data.py
PYTHONPATH=src python -m product_variant_resolver.evaluation
PYTHONPATH=src python scripts/train_calibration.py --output-directory artifacts
PYTHONPATH=src python scripts/generate_evaluation_report.py \
  --output-directory reports/fixture-v1
```

Generated calibration and policy files can be selected with `PVR_CALIBRATION_ARTIFACT` and
`PVR_POLICY_ARTIFACT`. Without them, the API uses the explicit fixture fallback versions.

## Demonstrated result

The checked-in report covers exactly **21 synthetic fixture test cases** (12 matched) drawn from a
120-product synthetic/curated catalog and a 100-case grouped benchmark.

| Metric | fixture-v1 test result |
|---|---:|
| Recall@25 | `1.0` |
| Top-1 accuracy | `1.0` |
| Hard-negative accuracy | `1.0` (4/4) |
| Precision | `1.0` |
| False-match rate | `0.0` |
| Coverage | `0.8333` |
| Heuristic reranker gain over RRF | `0.0` |
| Warmed in-process ASGI p95 | `7.9523 ms` |

The latency value uses 21 sequential in-process FastAPI/TestClient samples after five excluded
warm-ups at K=25. A separate QA regeneration reported `2.45 ms`, illustrating expected smoke-run
variance at this scale. Neither figure includes Docker,
TCP/network, a reverse proxy, PostgreSQL, or concurrency. See the
[versioned report](reports/fixture-v1/evaluation-fixture-v1-test.md),
[QA review](specs/product-variant-resolver/review.md), and
[MVP evidence](docs/evidence/product-variant-resolver-mvp.md).

## Docker and PostgreSQL status

The default Compose service is configured for the offline fixture path:

```bash
docker compose config --quiet
docker compose build api
docker compose up --wait api
docker compose down
```

An optional `postgres` profile defines pgvector and Alembic migration services:

```bash
docker compose --profile postgres up --wait postgres migrate
docker compose --profile postgres down
```

Only static Compose configuration was verified; the Docker daemon was unavailable during QA.
These commands are the intended next runtime check, not recorded successful evidence. The
PostgreSQL profile does not switch API resolution: PostgreSQL ingestion, FTS, and exact pgvector
execution remain deferred, and `PVR_BACKEND=postgres` intentionally fails readiness.

## Limitations

- `fixture-v1` is synthetic/curated. The numbers do not establish production accuracy, broad Hot
  Wheels coverage, or production readiness.
- `hashing-v1` is a deterministic baseline, not a neural embedding model. No pinned external
  embedding or cross-encoder artifact was integrated or evaluated.
- Docker/container, PostgreSQL/pgvector, external models, Python 3.12, real network latency, and
  concurrent load were not runtime-verified.
- UI behavior was verified with a Node DOM harness, not a live browser.
- Architect, security, and performance-agent reviews were deferred under Lite/MVP Mode. The local
  loopback debug endpoint needs access control or disabling before non-local exposure.

Decision history and remaining debt are recorded in
[MVP decisions](docs/decisions/product-variant-resolver.md) and the
[project log](docs/PROJECT-LOG.md).
