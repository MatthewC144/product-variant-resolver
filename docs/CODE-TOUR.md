# Code Tour

This is the shortest implementation path for an interviewer or new contributor. The active package
is under `src/product_variant_resolver/`; many additional modules preserve historical experiments
and governance workflows.

## 1. `signals.py` — understand the input

Normalizes a noisy title and extracts year, identifiers, color hints, series hints, and tokens. Look
for the distinction between observed evidence and missing evidence.

## 2. `retrieval.py` — build a high-recall candidate pool

Implements sparse retrieval, deterministic `hashing-v1` similarity, structured evidence, and RRF.
Look for soft structured conflicts and deterministic tie-breaking.

## 3. `rerank.py` — reorder candidates

Defines the reranker interface, the deterministic ablation, and Pointwise adapters. The neural path
changes ordering within a frozen pool; it does not mint identities.

## 4. `calibration.py` — estimate correctness

Converts ranking features into calibrated probability. Look for the explicit feature schema and the
separation between a ranker's raw score and a probability of correctness.

## 5. `policy.py` — decide or abstain

Turns calibrated evidence into `matched`, `ambiguous`, or `no_match`. This is where false-match risk
becomes an explicit product behavior rather than an implicit Top-1 assumption.

## 6. `service.py` — compose the resolver

Loads the catalog, builds retrieval/reranking/calibration dependencies, enforces runtime eligibility,
and constructs the response. Look for fail-closed dependency checks and the Human Knowledge
authority boundary.

## 7. `api.py` — expose the contract

Defines FastAPI startup, `/resolve`, and `/health`. Debug evidence is opt-in and bounded; abstentions
do not expose a canonical UUID.

## Evaluation entry point

`serper_dual_source_evaluation.py` is the best current evaluation example. It binds a grouped split,
frozen Pointwise configuration, aggregate-only final output, and source-specific metrics. For the
human-readable outcome, start with [Results](RESULTS.md) before reading the orchestration module.

## Active versus historical code

The seven modules above are the core review path. Modules prefixed with `domain_ranker_`,
`representative_benchmark_`, `release_casting_review_`, and many `human_knowledge_*_development`
names are reproducible experiment/governance tooling. They remain valuable evidence but are not all
executed by the default API.

