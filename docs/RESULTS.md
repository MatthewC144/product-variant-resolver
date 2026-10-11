# Results

This page separates the current portfolio headline from historical benchmarks and negative
experiments. Each section answers one question and states the conclusion without reproducing the
full experiment chronology.

## 1. Current ranking result — paired Image/Lens and Shopping

**Question:** Does the selected Pointwise cross-encoder improve release ranking across two
search-result sources?

**Result:** On 100 source observations from 50 held-out identities:

| Metric | RRF | Pointwise cross-encoder |
|---|---:|---:|
| Exact-release Top-1 | 55% | **64%** |
| Casting Top-1 | 86% | **95%** |
| MRR@10 | 0.722 | **0.792** |
| Recall@10 | 99% | 98% |
| Recall@25 | 99% | 99% |

**Conclusion:** Pointwise improved exact ordering while preserving deep candidate recall, with a
one-point Recall@10 trade-off. This is the primary portfolio result, not runtime-policy accuracy.

Evidence: [frozen result](../data/evaluation/serper-dual-source-evaluation-v1/raw-pointwise-final-test.json) ·
[QA](../specs/serper-dual-source-evaluation-v1/review.md) ·
[AI eval](evidence/ai-evals/serper-dual-source-raw-pointwise-final-test-v1.md)

## 2. Historical single-source release ranking

**Question:** Did neural reranking improve over RRF on the earlier image-search-derived benchmark?

**Result:** On the fixed 53-case test, exact-release Top-1 moved from `29/53` (54.72%) to
`36/53` (67.92%); casting Top-1 moved from `46/53` (86.79%) to `52/53` (98.11%).

**Conclusion:** The result selected Pointwise for later offline evaluation, but it is secondary
historical evidence because the newer paired benchmark better tests source transfer.

Evidence: [final comparison](../data/evaluation/image-search-release-ranking-v1/final-comparison.json)

## 3. Historical saturated fixture — negative result

The first experiment used a **100-case synthetic/curated fixture benchmark**. Its 21-case test split
contained only 12 matched ranking targets and all arms saturated:

| Arm | Top-1 | MRR@10 | Hard-negative | Recall@25 | Resolver p95 | Gate result |
|---|---:|---:|---:|---:|---:|---|
| RRF | `12/12` | `12/12` | `4/4` | `12/12` | `1.398 ms` | Runtime baseline |
| Neural pointwise | `12/12` | `12/12` | `4/4` | `12/12` | `89.164 ms` | FAIL: no Top-1 gain |
| Neural listwise | `12/12` | `12/12` | `4/4` | `12/12` | `89.583 ms` | FAIL: no Top-1 gain |

The formal result is **`winner: null`**. It does not establish production accuracy or statistical
generality. The value of this experiment was identifying a saturated benchmark and motivating the
larger real-catalog evaluation.

Evidence: [comparison report](../reports/neural-reranker-comparison-v1/comparison.md)

## 4. Domain-adapted pairwise ranker — negative result

**Question:** Does RankNet-style fine-tuning on query-supported same-casting hard negatives beat the
generic MiniLM Pointwise model?

**Result:** The V2 selection result is also `winner: null`. Seed 17 improved exact Top-1 from
`23/30` to `24/30`, but it missed the preregistered +3-case, MRR, and same-family gates. Seed 29 did
not improve exact Top-1.

**Conclusion:** No v2 checkpoint is selected for calibration, final evaluation, or runtime. The
pipeline demonstrates hard-negative mining, two-seed training, safetensors packaging, ONNX
equivalence, and disciplined rejection of a marginal result.

Evidence: [selection result](../data/evaluation/domain-ranker-v2-remediation/ranker-selection.json) ·
[selection evidence](evidence/domain-ranker-v2-selection.md)

## 5. Confidence calibration and selective prediction

**Question:** Can the selected ranker support a useful high-precision match/abstain operating point?

**Result:** The earlier frozen policy accepted 5/53 positive cases, all exact, and produced zero
false matches on 20 catalog-relative negatives, but abstained on 54/73 combined cases (73.97%). A
newer source-matched development comparison selected logistic calibration by Brier score (`0.1905`)
but could not meet the preregistered five-accept / 90%-precision threshold.

**Conclusion:** Calibration safety checks passed narrowly, but usable coverage did not. No new
policy was emitted, the fresh holdout remained sealed, and neural runtime activation remains off.

Evidence: [balanced result](../data/evaluation/image-search-pointwise-balanced-holdout-v1/results.json) ·
[source-matched calibration QA](../specs/serper-dual-source-policy-calibration-v1/review.md)

## 6. ONNX inference optimization

**Question:** Can the same model ordering be evaluated within the CPU latency budget?

**Result:** Float32 ONNX preserved all 180 frozen Top-25 orderings across 4,500 pairs; maximum logit
delta was `1.48e-05`. The repair benchmark reduced generic CPU p95 from `217.70 ms` to `103.65 ms`.

**Conclusion:** ONNX supplied an equivalent, faster evaluation substrate. It was not activated as
the FastAPI runtime default.

Evidence: [latency repair](../data/evaluation/domain-ranker-v2-remediation/latency-repair.json)

