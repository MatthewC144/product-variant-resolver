# Neural reranker architecture comparison v1 — Design

Date: 2026-09-25. Mode: Lite / Lean Industrial. Status: **COMPLETE — formal result `winner: null`; RRF remains runtime default**.

## 1. Overview

This feature is an isolated shadow experiment around the existing canonical retrieval path. It
freezes one candidate list per query and compares three orders over that same list:

1. `rrf`: preserve the current RRF order;
2. `neural_pointwise`: independently score each query/candidate text pair with a local Cross-Encoder;
3. `neural_listwise`: pass every candidate's frozen pointwise score plus generic retrieval and
   structured features through a small candidate-set attention network, then score the list with a
   listwise softmax objective.

It does not replace the runtime `PointwiseReranker`, enable a model in FastAPI, retrain calibration,
or join Human Knowledge RAG candidates with canonical candidates. The comparison has its own module,
CLI, artifacts, tests, and final recommendation. A passing recommendation is still shadow-only;
runtime work requires a later specification.

## 2. Why these model choices

### 2.1 Pointwise: MiniLM Cross-Encoder

Use `cross-encoder/ms-marco-MiniLM-L6-v2` as the single pointwise architecture. The model card marks
it as Apache-2.0 and demonstrates a `CrossEncoder` that accepts query/document pairs and emits one
ranking score. The architecture is a six-layer MiniLM/BERT sequence classifier, small enough for a
bounded CPU portfolio experiment while still being an actual neural cross-encoder.

The acquisition step SHALL pin the immutable Hugging Face revision
`233902d25c440f23af6f7d6e94d2946bac0bee0a`, download only the tokenizer/config plus
`model.safetensors`, reject pickle weights, record every file SHA-256, and store the files under the
gitignored `model-cache/neural-reranker-comparison-v1/pointwise/`. Runtime loading uses
`trust_remote_code=False`, `local_files_only=True`, CPU, float32, one output label, and
`max_length=128`.

V1 keeps the pretrained pointwise weights frozen. Only 36 matched train queries exist, which is too
small to justify full transformer fine-tuning without turning this Lite experiment into a fragile
overfitting exercise. The pretrained model is therefore the controlled text relevance baseline;
project-specific learning happens only in the small listwise head. Dev validates the frozen
pointwise configuration but does not search a model zoo or choose a favorable checkpoint.

Pointwise input is deterministic:

```text
query: <normalized marketplace title>

candidate:
brand=<brand> | casting=<casting> | year=<release_year> | series=<series> |
color=<color> | collector=<collector_number> | series_position=<series_position> |
edition=<edition> | aliases=<sorted aliases> | identifiers=<sorted identifiers>
```

Missing values use the literal `<missing>`. Canonical IDs, UUIDs, provenance, case IDs, split names,
labels, row order, and Human Knowledge fields never enter the model text. Every pair is scored in
one batched call per query; changing pair batch order must reproduce the same identity-to-score map
within `1e-6` on the same host/runtime.

References:

- Model card and license: <https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2>
- Cross-Encoder training/inference contract: <https://www.sbert.net/docs/cross_encoder/training_overview.html>

### 2.2 Listwise: permutation-equivariant candidate-set head

Use a small PyTorch candidate-set network rather than a generative LLM or a second independently
scored pointwise model. For every candidate, the frozen feature encoder creates the following
21-dimensional vector in this exact order:

```text
1   pointwise_logit
2   rrf_score
3   reciprocal_rrf_rank
4-6 sparse/dense/structured source-present flags
7-9 reciprocal sparse/dense/structured source ranks
10-14 year/collector_number/series_position/color/series match flags
15-19 year/collector_number/series_position/color/series conflict flags
20  match_count / 5
21  conflict_count / 5
```

Only `pointwise_logit` and `rrf_score` use train-fitted mean/standard-deviation normalization; fixed
binary and reciprocal-rank features are not data-normalized. Normalization statistics are computed
from train candidates only and frozen before dev. A missing source rank produces presence `0` and
reciprocal rank `0`.

The `CandidateSetReranker` is deliberately small:

```text
Linear(21 -> 32) + GELU + LayerNorm
one TransformerEncoderLayer(d_model=32, nhead=4, dim_feedforward=64,
                            dropout=0.0, batch_first=True)
Linear(32 -> 1) per candidate
masked softmax across candidates
```

It has no candidate positional embeddings. Self-attention lets every output depend on the other
candidates while the lack of positional encoding makes the mapping permutation-equivariant: if the
input candidates are permuted, their scores must permute the same way after identities are mapped
back. Padding positions are masked both in attention and loss.

Training uses only matched train lists whose target exists in the frozen pool. The loss is
cross-entropy over the candidate logits with the one correct candidate as target—a listwise softmax
objective. Use CPU float32, seed `20260924`, deterministic PyTorch algorithms, AdamW with learning
rate `1e-3` and weight decay `1e-4`, batch size `8`, at most `100` epochs, and early stopping after
`10` epochs without dev MRR@10 improvement. Ties in dev MRR choose the earlier epoch. The selected
checkpoint and train-only normalization statistics are saved as `safetensors`; optimizer state is
not a release artifact.

This is a bounded Set-Transformer-style design: self-attention models interactions between set
elements, and no sequence position is allowed to define the result. The motivating architecture is
described in Lee et al., *Set Transformer: A Framework for Attention-based Permutation-Invariant
Neural Networks*: <https://proceedings.mlr.press/v97/lee19d.html>.

## 3. Architecture and execution flow

```text
committed catalog + fixture-v1 benchmark
                  |
        protocol/source validation
                  |
       unchanged canonical retrieval
 sparse + hashing dense + structured -> RRF Top-25
                  |
          one shared candidate pool
         /             |              \
  keep RRF order   MiniLM pair scores   MiniLM pair scores
      (arm 1)         (arm 2)                 |
                                      21-D candidate features
                                                |
                                 set-attention + listwise softmax
                                             (arm 3)
         \             |               /
        paired ranks, metrics, latency, gates
                       |
          recommendation or winner: null
```

`src/product_variant_resolver/neural_reranking.py` owns optional-dependency adapters, deterministic
candidate text/features, pointwise scoring, the listwise network, ranking and tie-breaking. It has
no import path from `service.py`, so installing the core package continues to work without Torch.

`src/product_variant_resolver/neural_reranker_comparison.py` owns benchmark validation, phase gates,
artifact schemas, hashing, candidate collection, train/dev selection, test collection, metrics and
the installed CLI. Imports of Torch, Transformers and Sentence Transformers remain lazy and produce
an actionable optional-dependency error.

The existing `rerank.py`, `service.py`, `api.py`, settings, calibration, policy and Human Knowledge
modules stay unchanged in v1.

## 4. Phased CLI contract

Install one command:

```text
pvr-compare-neural-rerankers --root . <phase>
```

Exactly one phase is required.

### Phase A — `--acquire-model`

This is the only network-capable phase. It requires explicit `--confirm-license`, downloads the
pinned safetensors/tokenizer snapshot into `model-cache/`, rejects unexpected executable/pickle
files, and writes a local model manifest with repository, revision, Apache-2.0 declaration, file
hashes and dependency versions. It never contacts an inference API. A later implementation must ask
for network permission at execution time; this design does not perform the download.

### Phase B — `--freeze-protocol`

Validate the local model manifest, benchmark/catalog checksums, 100/58/21/21 denominators and family
separation. Freeze the comparison config and collect label-free train/dev candidate pools. The pool
contains query, orchestration-only case ID/split, extracted signals, retrieval timings and candidates,
but no expected status/UUID, neural score, model choice or winner.

### Phase C — `--fit`

Join only train/dev labels in memory. Compute the frozen pointwise logits for train/dev, fit
train-only feature normalization, train the listwise head on train, early-stop on dev MRR@10, and
freeze one pointwise manifest plus one listwise checkpoint/manifest. The test-label loader is not
imported by this phase. Existing model-selection bytes validate and return `unchanged`.

### Phase D — `--collect-test`

Require frozen protocol and models. Load only test queries and build each test candidate list once
with the unchanged retriever. Clone the same candidate values into all three arms, collect RRF,
pointwise and listwise scores/ranks plus stage timings, and persist raw label-free rows exactly once.
The phase rejects expected labels recursively and does not compute accuracy or choose a winner.

The warmed reference path uses five non-test train queries before collection. Per test case, common
signal/retrieval time is measured once; RRF has zero extra rerank time, pointwise includes the one
MiniLM batch, and listwise includes that same MiniLM batch plus its set head. For the reported shadow
resolver p95, each arm adds the measured common signal/retrieval time, its rerank time, and the
unmodified calibration/policy execution time on a cloned list. Those decisions are latency-only
diagnostics because the existing calibrator was not trained for neural logits.

### Phase E — `--score`

Validate raw bytes, then and only then join test targets. Recompute every rank and metric, apply the
predeclared NRC-R12/R13 gates, and write the machine-readable report, Markdown report and SVG charts.
This phase cannot change models or raw rows. A passing arm is a shadow recommendation, not runtime
activation; if no arm passes every gate, scoring produces `winner: null`.

### Phase F — `--check`

Read-only validation for whichever complete phase exists. It recomputes hashes, schemas, counts,
feature order, model manifest/checkpoint bindings, candidate equality, scores, metrics and gate
selection. Partial or contradictory phase state is invalid.

## 5. Interfaces

```python
class PointwiseScorer(Protocol):
    version: str
    def score_pairs(self, pairs: list[tuple[str, str]]) -> list[float]: ...

class ListwiseScorer(Protocol):
    version: str
    def score_set(self, features: list[list[float]]) -> list[float]: ...

def render_candidate_text(candidate: FrozenCandidate) -> str: ...
def candidate_feature_vector(candidate: FrozenCandidate, pointwise_logit: float) -> tuple[float, ...]: ...
def rank_scores(candidates: list[FrozenCandidate], scores: list[float]) -> list[RankedCandidate]: ...
```

`rank_scores` sorts score descending, then original RRF rank ascending, then canonical UUID only as
a final deterministic tie-break. UUID is never passed into either model.

The experiment module exposes pure functions for safe division, Recall@k, Top-1, MRR@10,
hard-negative accuracy, percentiles, per-category grouping, paired rank transitions, gate evaluation,
canonical JSON hashing and phase validation. File-writing wrappers use exclusive creation.

## 6. Artifact layout and data models

```text
config/neural-reranker-comparison-v1.json
model-cache/neural-reranker-comparison-v1/        # gitignored local model files
data/evaluation/neural-reranker-comparison-v1/
  protocol/protocol.json
  protocol/protocol-manifest.json
  pool/train-dev-candidate-pool.json
  pool/train-dev-candidate-pool-manifest.json
  models/pointwise-manifest.json
  models/listwise-model.safetensors
  models/listwise-manifest.json
  raw/test-raw.json
  raw/test-raw-manifest.json
reports/neural-reranker-comparison-v1/
  comparison.json
  comparison-manifest.json
  comparison.md
  reranker-comparison.svg
  accuracy-latency.svg
```

The repository commits protocol, public pools, the small project-trained listwise safetensors file,
manifests, label-free raw rows and final reports. It does not commit the third-party MiniLM weights;
their immutable source and local hashes remain reproducible through the acquisition manifest.

Primary schemas:

- `FrozenCandidate`: canonical UUID/ID, ordered public product fields, source ranks/scores,
  structured matches/conflicts, RRF rank/score.
- `CandidatePoolRow`: case ID, split, query, extracted signals, retrieval timings, ordered frozen
  candidates; no expected label.
- `ModelManifest`: model type, revision/source hashes, feature/input schema, seed, dependencies,
  training/dev bindings and selected epoch.
- `RawComparisonRow`: shared candidates, three score/rank maps and timings; no expected label or
  metric.
- `ScoredCase`: expected target/status joined after raw freeze, per-arm target rank and paired
  transition.
- `ComparisonReport`: counts, metrics, category metrics, latency, gates, selected recommendation or
  null, disclaimers and complete artifact bindings.

JSON uses sorted keys, UTF-8, finite numbers only, newline termination and SHA-256. Manifests bind
the exact source, catalog, benchmark, config, model, upstream artifact and output hashes.

## 7. Dependency and packaging plan

Keep neural packages optional. Add a `reranking` extra rather than expanding the default API install:

```toml
reranking = [
  "sentence-transformers==3.4.1",
  "torch==2.7.1",
  "safetensors>=0.5,<1",
]
```

The implementation task must resolve and record transitive versions in a dedicated
`constraints/reranking-python312.txt` after installing on the reference Mac CPU. The existing
`ml` extra remains unchanged until dependency verification proves that merging extras is safe.
Core unit tests use fake scorers and do not require neural packages; neural contract/integration
tests are marked and run only in the reranking environment.

Sentence Transformers 3.4.1 is retained because it matches the repository's existing `<4` range,
supports Python 3.12, and avoids an unrelated major-version migration during this experiment.
PyTorch 2.7.1 has a Python 3.12 macOS ARM64 wheel and provides the attention/listwise primitives.

## 8. Error handling and fail-closed rules

- Missing optional dependencies: stop before any artifact write with the exact install command.
- Missing model files, revision drift, license not confirmed, or SHA mismatch: stop before pool
  collection.
- Unexpected pickle, executable code, `trust_remote_code`, or network access outside acquisition:
  reject the model state.
- Benchmark count/family/checksum drift: require a new experiment version.
- Non-finite pointwise/listwise values, wrong feature width/order, duplicate candidate identity,
  noncontiguous ranks, or more than 25 candidates: reject the phase.
- Train/dev label leakage or any expected-label key in pool/raw: reject recursively.
- Test target absent: preserve `rank=null`; never inject the target.
- Existing valid bytes: return `unchanged`. Existing invalid/partial bytes: fail without overwrite.
- Pointwise batch-order or listwise permutation tolerance failure: model is ineligible before test.
- A test collection error is persisted without retry; scoring reports the error and cannot qualify a
  winner.

## 9. Security and provenance notes

The only new external input is a public model snapshot. The acquisition boundary is explicit,
revision-pinned and license-confirmed. Safetensors is required; remote Python code and pickle model
loading are forbidden. The comparison contains no credentials, personal data, private shadow
queries, or database writes. Model inference is local and offline after acquisition.

Public catalog text and synthetic benchmark queries may be committed in derived pools because they
already exist in this repository. Third-party weights stay gitignored to avoid repository bloat and
license ambiguity. The final report records the model publisher, immutable revision, Apache-2.0
license and file checksums rather than redistributing the weights.

## 10. Testing strategy

### Unit tests without neural dependencies

- Benchmark denominators, family isolation and checksum drift.
- Candidate text allowlist and explicit exclusion of IDs/provenance/labels.
- Candidate pool label-blind recursive validator.
- Exact 21-feature order, missing-rank behavior and train-only normalization.
- Deterministic rank/tie-breaking, metrics, paired transitions and NRC-R12/R13 null/winner gates.
- Artifact canonicalization, exclusive creation, idempotent `unchanged`, partial/tampered rejection.
- Fake pointwise batch-order invariance and fake listwise permutation mapping.

### Neural contract tests

- Pinned local model loads with `local_files_only=True` and returns one finite logit per pair.
- Reordered pointwise batches preserve identity-to-score values within `1e-6`.
- Listwise padding masks do not change real-candidate scores.
- Candidate permutations reproduce mapped listwise scores within `1e-6`.
- One optimizer step changes train loss without reading test labels; fixed seed reproduces selected
  epoch and checkpoint hash on the reference environment.

### Integration and CLI tests

- Synthetic temporary 58/21/21 pipeline covers every phase without network.
- `--fit` cannot import/call the test-label loader.
- `--collect-test` calls retrieval exactly once per test case and writes no labels.
- `--score` cannot write without immutable raw/model/protocol bindings.
- No model qualifies when any recall, hard-negative, MRR or latency gate fails.
- Full repository regression confirms API, runtime RRF, Dual RAG and PostgreSQL behavior unchanged.

### Final evidence

Before Phase B: Ruff, format, target strict MyPy, compile, focused tests and full suite. After every
material artifact phase: repeat focused/integration checks and `--check`. After scoring: full suite,
README/report consistency, manifest hashes, absent runtime diff and Git diff validation.

## 11. Design decisions and consequences

### D1 — Frozen pretrained pointwise model instead of fixture fine-tuning

This maximizes credibility per unit of data: it uses a real neural cross-encoder without pretending
that 36 positive train queries can safely adapt 22.7M parameters. The cost is domain mismatch; the
model may not improve over structured RRF. That null result is acceptable and informative.

### D2 — Listwise head consumes frozen pointwise plus explicit generic evidence

This directly tests whether candidate-relative context adds value over the same text scorer. The
head is small enough to train on 36 lists and its features are auditable. The cost is that listwise
latency includes pointwise latency and that it cannot recover text distinctions absent from the
frozen pointwise logit or generic structured features.

### D3 — Self-attention without positional encoding

Candidate rank is an explicit numeric feature, not an accidental tensor position. This allows the
model to use RRF evidence while preserving permutation equivariance. The critical failure mode is a
padding/order bug; mandatory permutation and mask tests block test collection if it appears.

### D4 — One architecture each, no model zoo

The portfolio question is Pointwise versus Listwise, not which of dozens of checkpoints wins on 12
test positives. One pointwise base and one bounded listwise head reduce selection bias, dependency
cost and narrative complexity. The trade-off is that a poor base checkpoint may produce a null
result; the project will report that rather than expanding search after seeing test.

## 12. Design confirmation checkpoint

The owner confirmed this design on 2026-09-24. That confirmation authorizes the atomic task-planning
step only. It does not yet download the model, install neural dependencies, build candidate pools,
train the listwise head, run test, change runtime, or modify the API. Build begins only after
`tasks.md` is also confirmed.
