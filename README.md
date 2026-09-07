# Product Variant Resolver

A Lite/MVP, offline-first resolver that maps noisy Hot Wheels marketplace titles to a canonical
fixture product—or abstains with `ambiguous` / `no_match`. The verified default is deliberately
dependency-light: catalog-derived signals, token sparse retrieval, deterministic `hashing-v1`
dense retrieval, structured soft conflicts, RRF, logistic confidence, and abstention behind
FastAPI.

This is a portfolio-quality fixture validation, not evidence of production accuracy or marketplace
coverage.

## Human-labeled auxiliary data

The repository also includes `data/human_labeled_names.json`, a frozen auxiliary corpus derived
from real noisy scans reviewed by a human. It contains 101 confirmed labels: 91 records pair an
initial recognition name with the human-verified name, while 10 retain an explicit `no_candidate`
initial failure and the human answer. The source and generated-file checksums are recorded in
`data/human_labeled_names_manifest.json`.

This corpus is currently intended for candidate-name evaluation, name normalization, and future
catalog alignment. It is deliberately excluded from the headline canonical-resolution metrics,
calibration training, and threshold selection because its names have not yet been mapped to this
repository's immutable catalog UUIDs and slugs.

The current conservative alignment is frozen in
`data/human_labeled_catalog_alignment.json`. Exact normalized brand/casting matching finds two
`Toyota Supra` records at casting-family level, but neither contains enough compatible variant
evidence to select one of the 12 synthetic Toyota Supra variants. The result is therefore 0
canonical mappings, 2 family-only matches, and 99 unmapped records. This low coverage is expected:
the fixture catalog has only 10 synthetic casting families, while the reviewed corpus contains 97
real casting names.

`data/human_backed_catalog.json` now turns those reviewed labels into a separate catalog draft:
97 stable casting entities and 100 provisional variant groups derived from all 101 records. One
exact duplicate structured label is merged while retaining both source cases and both human names.
The draft is eligible for sparse/dense candidate retrieval and human review, but every variant is
marked `needs_canonical_review`; it is not yet used for canonical API responses or calibration.

## Architecture

```text
Debug UI / API client
        |
 FastAPI: /resolve, /health
        |
 generic signal extraction
        |
        +------------------------------+
        |                              |
 canonical catalog RAG          human knowledge RAG
 sparse + dense + structured    sparse + hashing dense
        |                              |
 RRF + calibration/policy       provisional review evidence
        +------------------------------+
        |
 matched | ambiguous | no_match + debug evidence
```

Product knowledge—aliases, colors, series, identifiers, and variant attributes—lives in the
catalog. Conflicting structured signals remain soft ranking evidence instead of removing a
candidate. RRF stays on the default runtime path because the local heuristic reranker added `0.0`
absolute Top-1 accuracy on the frozen test; enable it only for an explicit experiment with
`PVR_RERANKER_ENABLED=true`. No external cross-encoder was evaluated.

The runtime now uses two retrieval corpora. The canonical fixture catalog is the only source allowed
to produce a final UUID. The human-backed catalog independently retrieves similar reviewed names and
shows them as `needs_canonical_review` evidence in debug mode. A human-only hit can help explain a
`no_match`, but cannot silently become a canonical product.

## Start the offline path

The source checkout remains convenient for development. Host QA used Python 3.14.6; the separately
verified Docker runtime uses the project-targeted Python 3.12.14.

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
python scripts/import_human_labeled_names.py --source /path/to/labeling-queue.csv
python scripts/align_human_labeled_names.py
python scripts/build_human_backed_catalog.py
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

| Metric | Evidence result |
|---|---:|
| Recall@25 | `1.0` |
| Top-1 accuracy | `1.0` |
| Hard-negative accuracy | `1.0` (4/4) |
| Precision | `1.0` |
| False-match rate | `0.0` |
| Coverage | `0.8333` |
| Heuristic reranker gain over RRF | `0.0` |
| Warmed in-process ASGI p95 | `7.9523 ms` |
| Host→Docker loopback p95 | `4.721208 ms` |

The in-process value uses 21 sequential FastAPI/TestClient samples after five excluded warm-ups at
K=25. A separate QA regeneration reported `2.45 ms`, illustrating expected smoke-run variance at
this scale. The host→Docker value is the separately scoped loopback artifact described below. See the
[versioned report](reports/fixture-v1/evaluation-fixture-v1-test.md),
[QA review](specs/product-variant-resolver/review.md), and
[MVP evidence](docs/evidence/product-variant-resolver-mvp.md).

## Docker and PostgreSQL status

The default offline Compose service is runtime-verified on Docker Desktop 29.5.3/aarch64 with
Python 3.12.14. The image ran as non-root `pvr` (UID 100), kept its root filesystem read-only,
used `/tmp` as its writable tmpfs, published only `127.0.0.1:8000`, and reached healthy readiness.
QA exercised the UI assets, all three decision states, default debug omission, request IDs, and a
dedicated missing-catalog container that failed closed with health/resolve 503 and no identity.

```bash
docker compose config --quiet
docker compose build api
docker compose up --wait api
curl --fail http://127.0.0.1:8000/health
docker compose down
```

The installed `pvr-report` CLI is also verified inside the rebuilt read-only Python 3.12 image. It
generated and validated JSON, Markdown, and four SVG files under writable `/tmp`:

```bash
docker compose run --rm --no-deps api \
  pvr-report --output-directory /tmp/pvr-report
```

The report CLI's in-process ASGI samples still record `container.measured=false`; real
host-to-container timing is a separate artifact. On the same single arm64 machine, 50 sequential
loopback requests after 10 warm-ups produced nearest-rank p95 **`4.721208 ms`** at concurrency 1.
The measurement includes the host HTTP client, Docker Desktop port forwarding, Uvicorn/FastAPI,
the offline resolver, and JSON serialization/parsing. It excludes startup, TLS, reverse proxy,
remote networking, concurrent load, and PostgreSQL, so it is not production latency evidence. See
the [raw runtime artifact](reports/runtime-validation/docker-python312-http-latency.json).

An optional `postgres` profile defines pgvector, Alembic migration, and canonical-catalog
ingestion services:

```bash
docker compose --profile postgres up -d --wait postgres
docker compose --profile postgres run --rm migrate
docker compose --profile postgres run --rm ingest
docker compose exec postgres psql -U pvr -d pvr \
  -c 'SELECT COUNT(*) FROM product_variant;'
PVR_BACKEND=postgres docker compose --profile postgres up -d --wait api
docker compose --profile postgres down
```

The first `ingest` run writes all 120 fixture variants plus aliases, identifiers, provenance,
full-text source documents, and version metadata in one transaction. Repeating it with the same
catalog leaves the stored rows unchanged. Identity or identifier collisions roll back the entire
attempt. `docker compose --profile postgres down` keeps the named local volume; adding `-v` deletes
that volume and its data.

The default remains the fully offline Dual-RAG runtime. Setting `PVR_BACKEND=postgres` now moves the
canonical sparse candidate source to PostgreSQL FTS after validating catalog version, checksum, and
row counts at startup. Dense canonical retrieval still uses the in-memory `hashing-v1` baseline,
and human-knowledge retrieval remains a separate non-canonical source. Exact pgvector execution is
deferred to T10.

## Limitations

- `fixture-v1` is synthetic/curated. The numbers do not establish production accuracy, broad Hot
  Wheels coverage, or production readiness.
- `hashing-v1` is a deterministic baseline, not a neural embedding model. No pinned external
  embedding or cross-encoder artifact was integrated or evaluated.
- The verified PostgreSQL sparse path covers one local arm64 machine, 120 fixture products, and
  sequential smoke requests. TLS, proxying, remote networking, concurrent load, PostgreSQL latency,
  pgvector execution, and external models were not measured.
- Runtime dependencies use bounded ranges without a committed lockfile or constraints file, so a
  future build may resolve different compatible versions. `pvr-report` requires runtime
  `httpx2>=2,<3`; the dev extra still carries legacy `httpx`, which emits a host-side warning.
- UI behavior was verified with a Node DOM harness, not a live browser.
- Architect, security, and performance-agent reviews were deferred under Lite/MVP Mode. The local
  loopback debug endpoint needs access control or disabling before non-local exposure.

Decision history and remaining debt are recorded in
[MVP decisions](docs/decisions/product-variant-resolver.md) and the
[project log](docs/PROJECT-LOG.md).
