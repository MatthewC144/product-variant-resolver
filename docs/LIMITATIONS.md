# Known Limitations and Claim Boundaries

This is the canonical human-readable limitations page. Detailed QA and immutable manifests may add
experiment-specific constraints, but public summaries should not contradict these boundaries.

## Data

- The 1,763-release catalog is a frozen, attributed third-party community snapshot. It is not a
  Mattel-certified, complete, or globally canonical catalog.
- The primary benchmark uses API-collected Image/Lens and Shopping result text, not organic
  marketplace queries or production traffic.
- The final `n=100` denominator is 100 source observations from 50 identities, not 100 independent
  products.
- Unsupported color and edition fields remain null rather than being inferred as truth.

## Evaluation

- The primary `55% → 64%` result measures exact-release ranking, not end-to-end decision-policy
  accuracy, screenshot accuracy, pricing accuracy, or business impact.
- The older 53-case test is secondary historical evidence. It should not be combined statistically
  with the paired dual-source final.
- Several experiment sets are intentionally small. They support engineering decisions, not broad
  claims of statistical generality.
- Search-result collection reflects one bounded collection period and provider behavior.

## Models and confidence

- `hashing-v1` is deterministic hashing-based similarity, not a learned semantic embedding model.
- Pointwise, Listwise, pairwise-finetuned, and ONNX paths are evaluated offline; none is the default
  FastAPI reranker.
- Cross-encoder logits and RRF scores are ranking signals, not calibrated probabilities.
- The current calibrated policy has inadequate match coverage and is not runtime-eligible. A fresh
  source-matched holdout remains sealed because development failed the operating-point gate.

## Authority

- Human Knowledge is supporting review/explanation evidence. It cannot create, promote, or replace
  a canonical UUID.
- Twenty exact releases were owner-reviewed relative to one frozen community revision. This is not
  manufacturer or global truth and does not promote the entire source.
- Historical blocked audits and rejected checkpoints remain valid historical records alongside
  later versioned evidence.

## Engineering and operations

- Production concurrency, sustained PostgreSQL load, remote networking, TLS, operational SLOs, and
  broad marketplace coverage have not been established.
- The repository preserves extensive research/governance code. The active runtime path is clean,
  while whole-repository static-analysis debt remains documented historical debt.
- Large retained checkpoints and reports make the Git repository heavier than a typical application
  repository; see the [artifact policy](ARTIFACT-POLICY.md).

## Safe summary

The project demonstrates measurable neural ranking gains, disciplined model rejection, calibrated
abstention design, reproducible evaluation, and explicit authority boundaries. It does not claim a
deployed production service, universal accuracy, or manufacturer-certified identity truth.

