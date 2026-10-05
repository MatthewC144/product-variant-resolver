# Product Variant Resolver

## Confidence-Aware Product Entity Resolution for Noisy Marketplace Listings

Product Variant Resolver maps noisy Hot Wheels marketplace titles to canonical product variants
using hybrid retrieval, structured evidence, calibrated abstention, and a provenance-aware
human-review boundary.

> **Scope disclosure:** current headline evidence is a **100-case synthetic/curated fixture benchmark**
> backed by a 120-product fixture catalog. The Test split contains 21
> cases and 12 matched ranking targets. These measurements do not establish production accuracy,
> marketplace coverage, or statistical generality.

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
          +--> sparse retrieval -------------------+
          +--> similarity retrieval ---------------+---> RRF candidate fusion
          |    hashing-v1: deterministic, non-neural       |
          +--> structured evidence (soft conflicts) -------+
                                                            |
                                         confidence calibration
                                          + decision policy
                                                            |
                                     matched | ambiguous | no_match

Human Knowledge retrieval --------------------------------------> explanation and
                                                                 review evidence only
                                                                 (never UUID authority)
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
optional canonical retrieval/storage backend, while the dependency-light offline path remains the
default.

## Key engineering decisions

- **Use soft structured conflicts.** Contradictory marketplace metadata lowers support without
  prematurely deleting the correct candidate.
- **Fuse ranks with RRF.** The resolver can combine lexical, hashing-similarity, and structured
  evidence without treating incomparable raw scores as equivalent probabilities.
- **Calibrate before deciding.** A confidence model and explicit policy turn ranking evidence into
  `matched`, `ambiguous`, or `no_match`, making false-match risk visible.
- **Separate evidence from identity authority.** Human-reviewed knowledge can explain a decision but
  cannot bypass the canonical catalog contract.
- **Require measured value before adding model complexity.** The neural shadow experiment produced
  no ranking gain on the saturated fixture while adding substantial latency, so RRF remains the
  runtime default.

## Human-reviewed authority milestone

The repository now includes a separate, offline Canonical Authority Review pipeline. Using one
frozen, attributed community-reference revision and two explicit owner-review Gates, it established
20 distinct exact catalog-v2 variants across seven same-casting multi-release families, with zero
composition shortfalls. Exactness is limited to the evidence-backed casting, year, series, collector
number, series position and toy identifier fields; color and edition remain null.

The original RHB-T4 audit honestly recorded `0` eligible exact variants and remains unchanged. A
later CAR-T6 run published a separate versioned re-audit with `passed_exact_authority_gate`, rather
than rewriting history. This is authority/provenance evidence, not a real-marketplace accuracy
result, manufacturer certification or permission to begin RHB-T5. See the
[final CAR evidence](docs/evidence/canonical-authority-review-v1.md) and
[versioned RHB-T4 re-audit](docs/evidence/representative-hard-benchmark-authority-reaudit.md).

## Measured evaluation

**Fixture evidence only:** the checked-in evaluation uses 100 synthetic/curated benchmark cases, a
120-product fixture catalog, and a casting-family-grouped Test split of 21 cases. Only 12 Test cases
are matched ranking targets. Perfect counts below describe this frozen fixture, not real-marketplace
or production accuracy.

| Metric | Fixture result | Denominator / boundary |
|---|---:|---|
| Recall@25 | `12/12` (`1.0`) | matched Test targets |
| Top-1 accuracy | `12/12` (`1.0`) | matched Test targets |
| Hard-negative accuracy | `4/4` (`1.0`) | matched hard-negative targets |
| Resolver precision | `10/10` (`1.0`) | predicted matches |
| False-match rate | `0/9` (`0.0`) | non-match Test cases |
| Coverage | `10/12` (`0.8333`) | matched Test cases |
| Abstention rate | `11/21` (`0.5238`) | all Test cases |
| Warmed in-process HTTP p95 | `7.9523 ms` | 21 sequential samples after 5 warm-ups |

The fixture also saturated sparse retrieval, hashing similarity, RRF, and the heuristic reranker:
each retained perfect Top-1 on the 12 matched targets. This is useful
regression evidence, but it cannot establish the incremental value each method would provide on a
harder real-world benchmark. Exact counts, policy settings, ablations, and latency boundaries are in
the [versioned fixture report](reports/fixture-v1/evaluation-fixture-v1-test.md),
[QA review](specs/product-variant-resolver/review.md), and
[MVP evidence](docs/evidence/product-variant-resolver-mvp.md).

## Neural pointwise versus listwise comparison

An isolated offline shadow experiment compared the unchanged RRF order with a pinned MiniLM
pointwise cross-encoder and a candidate-set listwise attention model. All three arms consumed the
same frozen Top-25 canonical candidate pools. Neither neural arm is active in the FastAPI runtime.

| Arm | Top-1 | MRR@10 | Hard-negative | Recall@25 | Resolver p95 | Gate result |
|---|---:|---:|---:|---:|---:|---|
| RRF | `12/12` | `12/12` | `4/4` | `12/12` | `1.398 ms` | Runtime baseline |
| Neural pointwise | `12/12` | `12/12` | `4/4` | `12/12` | `89.164 ms` | FAIL: Top-1 gain `0.00 < 0.05` |
| Neural listwise | `12/12` | `12/12` | `4/4` | `12/12` | `89.583 ms` | FAIL: Top-1 gain `0.00 < 0.05` |

The formal result is **`winner: null`** and RRF remains the default. Both neural arms added
approximately 64× p95 latency without improving any of the 12 matched cases. This is a completed
negative experiment, not evidence that neural reranking never helps;
this small fixture does not establish production accuracy or statistical generality. See the
[immutable comparison report](reports/neural-reranker-comparison-v1/comparison.md),
[public evidence](docs/evidence/neural-reranker-comparison-v1.md), and
[comparison QA review](specs/neural-reranker-comparison/review.md).

## Limitations

- The catalog and 100-case benchmark are synthetic/curated fixtures; Test has only 21 cases and 12
  matched ranking targets.
- The fixture RRF baseline is saturated, limiting conclusions about the incremental value of dense
  similarity, structured retrieval, heuristic reranking, or neural reranking.
- Default `hashing-v1` similarity is deterministic and non-neural; it is not a learned semantic
  embedding model.
- Large-catalog behavior, approximate vector search, production concurrency, remote networking,
  TLS, and sustained PostgreSQL load have not been established.
- The current evidence does not establish real-marketplace accuracy, broad Hot Wheels coverage, or
  statistical generality.
- A representative real-world benchmark, hard-negative taxonomy, calibration analysis, and
  risk/coverage evaluation remain follow-up work.

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
| Human-labeled import and catalog alignment | [source manifest](data/human_labeled_names_manifest.json), [real-noisy-data evaluation](docs/evidence/ai-evals/human-labeled-real-noisy-v1.md), [alignment evaluation](docs/evidence/ai-evals/human-catalog-alignment-v1.md), [human-backed catalog evaluation](docs/evidence/ai-evals/human-backed-catalog-v1.md) |
| Human Knowledge, review-family authority, and retrieval evaluation | [family-level contract](specs/family-level-human-knowledge/requirements.md), [family QA](specs/family-level-human-knowledge/review.md), [v2 final evaluation](reports/family-retrieval-v2/evaluation.md), [final evidence](docs/evidence/family-retrieval-final-v2.md), [identity-bounded QA](specs/human-knowledge-identity-bounded-retrieval/review.md) |
| Human Knowledge experiments and negative results | [retriever redesign evidence](docs/evidence/human-knowledge-retriever-v3-implementation.md), [v4 identity development](reports/human-knowledge-identity-development-v1/selection.md), [identity contradiction](reports/human-knowledge-identity-contradiction-development-v1/selection.md), [identity envelope](reports/human-knowledge-identity-envelope-development-v2/historical-calibration.md), [claim graph](reports/human-knowledge-identity-claim-graph-development-v3/historical-calibration.md), [identity certificate](reports/human-knowledge-identity-certificate-development-v4/historical-calibration.md) |
| External Wiki pilot, adjudication, and review-family materialization | [source and license README](data/external/hot-wheels-wiki/README.md), [final family decisions](docs/evidence/fandom-priority-two-decisions-t44.md), [materialization evidence](docs/evidence/review-family-materialization-t46.md), [family projection evidence](docs/evidence/family-level-human-knowledge-t47.md) |
| Canonical Authority Review and versioned RHB-T4 Gate | [CAR requirements](specs/canonical-authority-review-v1/requirements.md), [final QA](specs/canonical-authority-review-v1/review.md), [final evidence](docs/evidence/canonical-authority-review-v1.md), [RHB-T4 re-audit](docs/evidence/representative-hard-benchmark-authority-reaudit.md) |
| Owner-supplied 2023–2026 staging and review | [staging report](reports/local-release-staging-v1/report.md), [casting review](reports/local-release-casting-review-v1/report.md), [owner-decision report](reports/local-release-casting-review-decisions-v1/report.md), [materialization report](reports/local-release-casting-review-family-materialization-v1/report.md), [knowledge projection](reports/local-release-casting-review-family-knowledge-v1/report.md), [shadow evaluation](reports/local-release-review-family-retrieval-evaluation-v1/report.md) |
| PostgreSQL, pgvector, and Human Knowledge storage | [catalog ingestion](docs/evidence/postgres-ingestion-t07.md), [sparse retrieval](docs/evidence/postgres-sparse-retrieval-t09.md), [dense retrieval](docs/evidence/postgres-dense-retrieval-t10.md), [isolated Human Knowledge storage](docs/evidence/t49-2-human-knowledge-postgres.md), [storage-profile SQL](docs/evidence/t49-3-storage-profile-sql.md), [file-runtime runbook](docs/runbooks/human-storage-file-runtime.md) |
| Runtime and Docker validation | [raw Docker loopback latency](reports/runtime-validation/docker-python312-http-latency.json), [runtime-package evidence](docs/evidence/t49-4-human-storage-runtime-package.md), [MVP evidence](docs/evidence/product-variant-resolver-mvp.md) |
| Portfolio positioning | [portfolio guide](docs/PORTFOLIO-GUIDE.md), [requirements](specs/portfolio-positioning-v1/requirements.md), [design](specs/portfolio-positioning-v1/design.md) |
| Engineering rationale and chronology | [decision record](docs/decisions/product-variant-resolver.md), [project log](docs/PROJECT-LOG.md), [real-catalog roadmap](docs/REAL-CATALOG-ROADMAP.md) |
