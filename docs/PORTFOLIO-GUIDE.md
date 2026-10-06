# Product Variant Resolver — Portfolio Guide

This guide turns the checked-in implementation and frozen evidence into resume and interview
language. Claims are intentionally bounded: the project is a portfolio-grade, high-precision
abstaining prototype, not a production or manufacturer-certified resolver.

## 1. Positioning

**Headline:** Confidence-aware product entity resolution for noisy marketplace listings.

**One-line description:** Product Variant Resolver maps noisy product titles to canonical release
identities through hybrid retrieval, Pointwise reranking, calibrated abstention, and a Dual-RAG
authority boundary that separates canonical catalog truth from human review knowledge.

Use **entity resolution** as the primary category. “Dual RAG” describes the internal two-corpus
architecture, not a generative answer system: only canonical catalog retrieval may emit a UUID;
Human Knowledge supplies review/explanation evidence and cannot promote identity. No LLM generates
the final answer.

## 2. Three resume bullets

- Built a confidence-aware product entity resolver in Python/FastAPI over a frozen 1,763-release third-party catalog, combining sparse search, deterministic hashing similarity, structured signals, RRF fusion, and a revision-pinned MiniLM Pointwise reranker; on a frozen 53-query catalog-present test, Pointwise improved exact-release Top-1 from `29/53` (54.72%) to `36/53` (67.92%) and casting Top-1 from `46/53` to `52/53`.
- Designed a hash-bound, output-blind evaluation pipeline for a calibrated `matched` / `ambiguous` / `no_match` policy; across 53 catalog-present and 20 catalog-relative negative cases, accepted positive precision was `5/5`, negative false matches were `0/20`, and the system honestly retained 73.97% abstention and a runtime HOLD instead of tuning on final holdouts.
- Implemented a Dual-RAG trust boundary and provenance workflow that keeps canonical UUID authority separate from Human Knowledge, stages 1,763 third-party release observations through optional PostgreSQL/pgvector infrastructure, and uses explicit owner Gates to freeze 20 evidence-backed exact variants while leaving unsupported color/edition null.

## 3. 60–90 second interview pitch

Marketplace titles are noisy: sellers abbreviate model names, omit years, mix collector numbers with
quantities, or attach incorrect colors and series. I built Product Variant Resolver as
confidence-aware entity resolution rather than asking an LLM to guess. It extracts structured
signals, retrieves candidates through sparse search, deterministic non-neural hashing similarity and
structured evidence, then fuses ranks with RRF. A local MiniLM Pointwise cross-encoder can rerank the
same frozen candidates, and a calibrated policy returns `matched`, `ambiguous`, or `no_match`.

The architecture is Dual RAG because canonical catalog retrieval and Human Knowledge retrieval have
different authority: only the catalog branch can return a canonical UUID, while Human Knowledge can
explain or support review without silently becoming product truth. On a frozen 53-query test over a
1,763-release community snapshot, Pointwise improved exact-release Top-1 by 13.21 percentage points
over RRF. I then evaluated the frozen decision policy output-blind on 53 positives plus 20 negatives.
It made no false matches on the negative holdout and every accepted positive was exact, but it
abstained on 74% of cases. I kept runtime disabled and documented that low coverage instead of
lowering thresholds on the test. That governance decision is as important as the model result.

## 4. What to show during a code review

1. Start with the [README architecture](../README.md#architecture) and explain why canonical and
   Human Knowledge retrieval have different authority.
2. Open the [53-case final ranking comparison](../data/evaluation/image-search-release-ranking-v1/final-comparison.json)
   and compare RRF, release heuristic, Pointwise and Listwise under identical Top-25 candidates.
3. Open the [balanced policy QA review](../specs/pointwise-balanced-holdout-evaluation-v1/review.md)
   and discuss precision, recall, abstention, output blindness and why runtime remains held.
4. Show [api.py](../src/product_variant_resolver/api.py) and [service.py](../src/product_variant_resolver/service.py)
   to connect the experiment architecture to the fail-closed FastAPI runtime.

## 5. Claim guardrails

| Topic | Safe claim | Do not claim | Evidence |
|---|---|---|---|
| Project category | Confidence-aware entity resolution with a Dual-RAG authority boundary | Generative RAG chatbot or LLM-generated answer system | [MVP evidence](evidence/product-variant-resolver-mvp.md) |
| Catalog | Frozen 1,763-release third-party community snapshot for staging/evaluation | Mattel-certified, complete or global Hot Wheels catalog | [source README](../data/external/hot-wheels-wiki/README.md) |
| Positive query data | 153 unique image-search-derived, catalog-bound queries; 100 development and 53 test | Representative live-marketplace traffic | [dataset](../data/evaluation/image-search-resolver-v1/dataset.json) |
| Ranking result | Pointwise exact Top-1 `36/53` vs RRF `29/53` on the frozen test | Production accuracy or universal superiority | [final comparison](../data/evaluation/image-search-release-ranking-v1/final-comparison.json) |
| Pointwise/Listwise | Local offline reranking arms over identical frozen Top-25 candidates | Active default FastAPI neural reranking | [ranking spec](../specs/image-search-release-ranking/mvp-brief.md) |
| Calibrated policy | Accepted positives `5/5`, negative false matches `0/20`, combined abstention 73.97% | “100% accurate,” high-coverage, or runtime-ready | [balanced QA](../specs/pointwise-balanced-holdout-evaluation-v1/review.md) |
| Similarity baseline | `hashing-v1` is deterministic, hashing-based and non-neural | Learned embedding model or semantic foundation model | [fixture report](../reports/fixture-v1/evaluation-fixture-v1-test.md) |
| Canonical authority | 20 owner-reviewed variants are exact relative to one frozen community revision; color/edition remain null | Manufacturer/global truth or source-wide canonical promotion | [CAR evidence](evidence/canonical-authority-review-v1.md) |
| PostgreSQL/pgvector | Optional, tested storage/retrieval infrastructure | Required default runtime or production-scale proof | [ingestion evidence](evidence/postgres-ingestion-t07.md) |

## 6. Technical stack and why it is present

| Component | Role in the project |
|---|---|
| Python 3.12 + Pydantic | Typed identity, evaluation and governance contracts |
| FastAPI | Fail-closed `/resolve` and `/health` interfaces with bounded debug output |
| Sparse + hashing similarity + structured signals | Dependency-light canonical candidate generation |
| Reciprocal Rank Fusion | Combines heterogeneous rankings without equating raw scores |
| MiniLM Pointwise cross-encoder | Local query/candidate reranking selected by measured development evidence |
| Project-trained Listwise head | Candidate-set comparison arm; measured but not selected |
| Logistic calibration + three-state policy | Turns ranking evidence into match, abstain or reject decisions |
| PostgreSQL + pgvector | Optional catalog/Human Knowledge persistence and retrieval profile |
| Pytest, Ruff, MyPy | Regression, integrity, privacy and static-quality gates |

## 7. Honest limitations and next engineering step

The strongest current result is not “100% accuracy.” It is a governed trade-off: accepted matches
were precise, but the frozen policy resolved too few positives and abstained on 54/73 combined cases.
The source is community-maintained, query generation is image-search-derived, and production traffic,
concurrency and broad catalog coverage are not established.

Do not reuse the 53 positive or 20 negative holdouts to lower thresholds. A legitimate coverage
improvement needs new development queries, a separately trained/recalibrated candidate policy, and a
fresh final test. Until then, present the system as a high-precision abstaining prototype whose
engineering strength is measurable ranking improvement plus explicit authority and evaluation
governance.
