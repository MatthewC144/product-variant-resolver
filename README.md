# Product Variant Resolver

## Confidence-Aware Product Entity Resolution for Noisy Marketplace Listings

Product Variant Resolver maps noisy Hot Wheels marketplace titles to canonical product variants
using hybrid retrieval, structured evidence, calibrated abstention, and a provenance-aware
human-review boundary.

> **Scope disclosure:** current headline evidence uses a frozen **1,763-release third-party
> community snapshot** and 153 image-search-derived queries (100 development / 53 test), plus an
> independently frozen 20-query catalog-relative no-match holdout. It is not Mattel-certified,
> live-marketplace traffic, production accuracy, or runtime authorization.

[Architecture](#architecture) · [Evaluation](#measured-evaluation) ·
[Neural comparison](#neural-pointwise-versus-listwise-comparison) ·
[Limitations](#limitations) · [Run locally](#run-locally) ·
[Deep evidence](#deep-evidence) · [Portfolio guide](docs/PORTFOLIO-GUIDE.md)

## Problem

Marketplace listings rarely follow a reliable schema. A title can abbreviate a casting name, omit a
year or color, mix a collector number with a seller lot number, or contain incorrect metadata.
Near-identical variants may differ only by year, series, color, or identifier, so a strong token
match is not always the correct product identity.

The resolver therefore treats a confident wrong match as worse than an honest abstention. Every
request ends in one of three observable outcomes:

- `matched` — evidence is sufficient to return one canonical UUID;
- `ambiguous` — plausible candidates remain, but the resolver cannot safely choose one;
- `no_match` — the catalog does not contain a sufficiently supported candidate.

## Architecture

```text
noisy marketplace title
          |
   signal extraction
          |
          +--> sparse retrieval -------------------------+
          +--> hashing-v1 similarity --------------------+--> RRF candidate fusion
          |    deterministic, non-neural                 |          |
          +--> structured evidence (soft conflicts) -----+          +--> optional local
                                                                     Pointwise reranking
                                                                              |
                                                               frozen calibration + policy
                                                                              |
                                                        matched | ambiguous | no_match

Human Knowledge retrieval --------------------------------> explanation and review evidence
                                                           only; never canonical UUID authority
```

The default similarity path uses `hashing-v1`, a deterministic hashing-based representation. It is
**not a learned neural embedding model**. Sparse, similarity-based, and structured retrieval create
independent rankings; Reciprocal Rank Fusion (RRF) combines them without assuming their raw scores
share a scale. Structured conflicts are soft ranking evidence rather than hard filters because
seller-supplied year, color, series, and identifier fields can be incomplete or wrong.

The internal **Dual-RAG** architecture separates two retrieval corpora by authority:

1. The **canonical catalog branch** is the only branch allowed to produce a canonical UUID.
2. The **Human Knowledge branch** retrieves provisional variants and accepted review-family
   evidence for explanation and debugging. It cannot silently create, promote, or replace a
   canonical identity.

No LLM generates the final answer. PostgreSQL full-text search and pgvector are available as an
optional canonical retrieval/storage backend, while the dependency-light RRF path remains the
runtime default. The measured Pointwise path is local and development-only: its frozen policy is
explicitly `runtime_eligible=false`.

## Key engineering decisions

- **Use soft structured conflicts.** Contradictory marketplace metadata lowers support without
  prematurely deleting the correct candidate.
- **Fuse ranks with RRF.** The resolver can combine lexical, hashing-similarity, and structured
  evidence without treating incomparable raw scores as equivalent probabilities.
- **Calibrate before deciding.** A confidence model and explicit policy turn ranking evidence into
  `matched`, `ambiguous`, or `no_match`, making false-match risk visible.
- **Separate evidence from identity authority.** Human-reviewed knowledge can explain a decision but
  cannot bypass the canonical catalog contract.
- **Require measured value before adding model complexity.** Neural reranking first showed no gain
  on a saturated fixture; after expanding to a 1,763-release corpus, Pointwise improved frozen-test
  exact-release Top-1, but its calibrated policy still abstains too often for runtime activation.

## Data and authority boundaries

The owner-supplied 2023–2026 export contains 1,763 third-party community release observations. It is
an evaluation/staging snapshot, not a manufacturer catalog. A separate owner-gated Canonical
Authority Review established 20 exact variants across seven multi-release families relative to one
frozen community revision; unsupported color and edition remain null.

Query authoring, label review, canonical promotion, development selection, final evaluation, and
runtime activation use separate hash-bound Gates. Historical blocked audits remain intact beside
later versioned passes instead of being rewritten. See the [CAR evidence](docs/evidence/canonical-authority-review-v1.md),
[release-source documentation](data/external/hot-wheels-wiki/README.md), and
[decision history](docs/decisions/product-variant-resolver.md).

## Measured evaluation

### Release-ranking evidence

The main ranking benchmark contains 153 unique image-search-derived queries bound to the frozen
1,763-release snapshot. Model selection used 100 development rows; the selected Pointwise ranker was
then evaluated once on the fixed 53-case test. Test labels did not fit either neural model.

| Frozen 53-case test metric | RRF | Release heuristic | Pointwise | Listwise |
|---|---:|---:|---:|---:|
| Casting Top-1 | `46/53` (86.79%) | `46/53` (86.79%) | **`52/53` (98.11%)** | `51/53` (96.23%) |
| Exact-release Top-1 | `29/53` (54.72%) | `33/53` (62.26%) | **`36/53` (67.92%)** | `32/53` (60.38%) |
| Exact-release Recall@25 | `53/53` | `53/53` | `53/53` | `53/53` |
| Rerank p95 | `0 ms` | `0.20 ms` | `130.49 ms` | `130.91 ms` |

Pointwise improved exact-release Top-1 by 7/53, or 13.21 percentage points, over RRF and remained
the winner selected on development. This is catalog-relative ranking evidence, not a deployed
runtime claim. See the [frozen final comparison](data/evaluation/image-search-release-ranking-v1/final-comparison.json)
and [ranking specification](specs/image-search-release-ranking/mvp-brief.md).

### Calibrated policy evidence

The selected ranker was wrapped in a five-feature logistic calibrator and frozen three-state policy.
An output-blind evaluation combined the fixed 53 catalog-present policy test with an independently
frozen 20-query catalog-relative no-match holdout. Only aggregate outputs were retained.

| Policy evidence | Result | Interpretation |
|---|---:|---|
| Accepted positive exact precision | `5/5` (100%) | every accepted positive had the correct full release |
| Positive exact recall | `5/53` (9.43%) | very low match coverage |
| Positive false no-match | `3/53` (5.66%) | below the pre-registered 10% ceiling |
| Negative no-match recall | `11/20` (55%) | 9/20 negatives remained ambiguous |
| Negative false matches | `0/20` (0%) | no known negative was incorrectly matched |
| Combined abstention | `54/73` (73.97%) | policy is conservative and not runtime-ready |

The pre-registered safety gate passed, but QA kept runtime on **HOLD** because coverage is too low.
Neither holdout may be used to lower thresholds or retune the model. See the
[balanced aggregate result](data/evaluation/image-search-pointwise-balanced-holdout-v1/results.json),
[QA review](specs/pointwise-balanced-holdout-evaluation-v1/review.md), and
[AI-eval rubric](docs/evidence/ai-evals/pointwise-balanced-holdout-v1.md).

## Neural pointwise versus listwise comparison

Both neural arms consume the same frozen Top-25 candidates. Pointwise scores each query/candidate
pair independently with a revision-pinned MiniLM cross-encoder. Listwise adds a project-trained
candidate-set attention head over shared candidate features. Neither is active in FastAPI.

The first 120-product fixture was saturated: RRF, Pointwise and Listwise all scored `12/12`, so the
honest result was `winner: null`. That negative result motivated a harder corpus instead of a stronger
claim. On the later 1,763-release benchmark, Pointwise achieved `36/53` exact-release Top-1 versus
RRF `29/53` and Listwise `32/53`. The project therefore demonstrates both outcomes: rejecting neural
complexity when it added no value, and selecting it when a harder benchmark measured a gain—while
still withholding runtime activation when calibration produced inadequate coverage.

See the [fixture null-result report](reports/neural-reranker-comparison-v1/comparison.md) and the
[real-catalog final comparison](data/evaluation/image-search-release-ranking-v1/final-comparison.json).

## Limitations

- The 1,763-release source is an attributed third-party community snapshot, not Mattel or global
  canonical truth; unsupported color and edition remain unknown.
- The 153 positive queries and 20 negatives are image-search-derived/catalog-relative evidence, not
  sampled live-marketplace traffic.
- The 53 positives were previously used for ranker evaluation, although not for Pointwise v2
  calibration or threshold selection; only the 20 negatives were fully frozen before policy access.
- Pointwise ranking improved, but the calibrated policy abstains on 73.97% of the combined test and
  is explicitly not runtime-authorized.
- Default `hashing-v1` similarity is deterministic and non-neural; it is not a learned embedding
  model. Pointwise/Listwise remain local offline evaluation paths.
- Production concurrency, remote networking, TLS, sustained PostgreSQL load, broad marketplace
  coverage and statistical generality have not been established.

## Run locally

The default path is offline and requires no external model or API key:

```bash
python -m pip install -e '.[dev]'
PYTHONPATH=src uvicorn product_variant_resolver.api:app --reload
```

Resolve one title:

```bash
curl --fail --json '{"title":"2022 Chevy Nomad Red #101","debug":true}' \
  http://127.0.0.1:8000/resolve
```

Check dependency readiness:

```bash
curl --fail http://127.0.0.1:8000/health
```

The debug UI is available at `http://127.0.0.1:8000/`. Normal responses omit internal candidates,
ranks, scores, and timings; `debug=true` returns a bounded explanation payload. Resolution logs omit
raw marketplace titles. For PostgreSQL and storage workflows, use the linked evidence and runbooks
below rather than treating the optional database profile as a prerequisite.

## Deep evidence

The landing page intentionally keeps chronological batch histories, checksums, adjudication notes,
staging audits, and validation transcripts out of the primary reading path. No underlying artifact
was deleted; the checked-in sources below remain the authoritative evidence.

| Category | Durable repository evidence |
|---|---|
| Core MVP, contract, and QA | [MVP brief](specs/product-variant-resolver/mvp-brief.md), [QA review](specs/product-variant-resolver/review.md), [public evidence](docs/evidence/product-variant-resolver-mvp.md), [fixture report](reports/fixture-v1/evaluation-fixture-v1-test.md) |
| Neural comparison | [comparison report](reports/neural-reranker-comparison-v1/comparison.md), [public evidence](docs/evidence/neural-reranker-comparison-v1.md), [QA review](specs/neural-reranker-comparison/review.md) |
| Real-catalog ranking and calibrated policy | [53-case final comparison](data/evaluation/image-search-release-ranking-v1/final-comparison.json), [three-class QA](specs/pointwise-three-class-development-calibration/review.md), [balanced policy QA](specs/pointwise-balanced-holdout-evaluation-v1/review.md), [AI-eval evidence](docs/evidence/ai-evals/pointwise-balanced-holdout-v1.md) |
| Human-labeled import and catalog alignment | [source manifest](data/human_labeled_names_manifest.json), [real-noisy-data evaluation](docs/evidence/ai-evals/human-labeled-real-noisy-v1.md), [alignment evaluation](docs/evidence/ai-evals/human-catalog-alignment-v1.md), [human-backed catalog evaluation](docs/evidence/ai-evals/human-backed-catalog-v1.md) |
| Human Knowledge, review-family authority, and retrieval evaluation | [family-level contract](specs/family-level-human-knowledge/requirements.md), [family QA](specs/family-level-human-knowledge/review.md), [v2 final evaluation](reports/family-retrieval-v2/evaluation.md), [final evidence](docs/evidence/family-retrieval-final-v2.md), [identity-bounded QA](specs/human-knowledge-identity-bounded-retrieval/review.md) |
| Human Knowledge experiments and negative results | [retriever redesign evidence](docs/evidence/human-knowledge-retriever-v3-implementation.md), [v4 identity development](reports/human-knowledge-identity-development-v1/selection.md), [identity contradiction](reports/human-knowledge-identity-contradiction-development-v1/selection.md), [identity envelope](reports/human-knowledge-identity-envelope-development-v2/historical-calibration.md), [claim graph](reports/human-knowledge-identity-claim-graph-development-v3/historical-calibration.md), [identity certificate](reports/human-knowledge-identity-certificate-development-v4/historical-calibration.md) |
| External Wiki pilot, adjudication, and review-family materialization | [source and license README](data/external/hot-wheels-wiki/README.md), [final family decisions](docs/evidence/fandom-priority-two-decisions-t44.md), [materialization evidence](docs/evidence/review-family-materialization-t46.md), [family projection evidence](docs/evidence/family-level-human-knowledge-t47.md) |
| Canonical Authority Review and versioned RHB-T4 Gate | [CAR requirements](specs/canonical-authority-review-v1/requirements.md), [final QA](specs/canonical-authority-review-v1/review.md), [final evidence](docs/evidence/canonical-authority-review-v1.md), [RHB-T4 re-audit](docs/evidence/representative-hard-benchmark-authority-reaudit.md) |
| Owner-supplied 2023–2026 staging and review | [staging report](reports/local-release-staging-v1/report.md), [casting review](reports/local-release-casting-review-v1/report.md), [owner-decision report](reports/local-release-casting-review-decisions-v1/report.md), [materialization report](reports/local-release-casting-review-family-materialization-v1/report.md), [knowledge projection](reports/local-release-casting-review-family-knowledge-v1/report.md), [shadow evaluation](reports/local-release-review-family-retrieval-evaluation-v1/report.md) |
| PostgreSQL, pgvector, and Human Knowledge storage | [catalog ingestion](docs/evidence/postgres-ingestion-t07.md), [sparse retrieval](docs/evidence/postgres-sparse-retrieval-t09.md), [dense retrieval](docs/evidence/postgres-dense-retrieval-t10.md), [isolated Human Knowledge storage](docs/evidence/t49-2-human-knowledge-postgres.md), [storage-profile SQL](docs/evidence/t49-3-storage-profile-sql.md), [file-runtime runbook](docs/runbooks/human-storage-file-runtime.md) |
| Runtime and Docker validation | [raw Docker loopback latency](reports/runtime-validation/docker-python312-http-latency.json), [runtime-package evidence](docs/evidence/t49-4-human-storage-runtime-package.md), [MVP evidence](docs/evidence/product-variant-resolver-mvp.md) |
| Portfolio positioning | [portfolio guide](docs/PORTFOLIO-GUIDE.md), [original positioning spec](specs/portfolio-positioning-v1/requirements.md), [current evidence-refresh QA](specs/portfolio-evidence-refresh-v2/review.md) |
| Engineering rationale and chronology | [decision record](docs/decisions/product-variant-resolver.md), [project log](docs/PROJECT-LOG.md), [real-catalog roadmap](docs/REAL-CATALOG-ROADMAP.md) |
