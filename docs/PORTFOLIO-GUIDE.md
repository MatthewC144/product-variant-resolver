# Product Variant Resolver — Portfolio Guide

This guide describes the repository as it exists today. Current claims below are limited to the
checked-in fixture and shadow-evaluation evidence; they are not production or real-marketplace
accuracy claims.

## 1. Positioning

**Headline:** Confidence-aware product entity resolution for noisy marketplace listings.

**One-line description:** Product Variant Resolver maps a noisy listing title to a canonical product
variant by combining sparse retrieval, deterministic hashing-based similarity, structured evidence,
RRF fusion, confidence calibration, and an explicit `matched` / `ambiguous` / `no_match` policy.

The project should be introduced as entity resolution because its user-visible job is to decide
whether a listing has enough evidence for one canonical identity—and to abstain when it does not.
“Dual RAG” remains useful as an internal architecture description: canonical catalog retrieval is
the only branch allowed to return a canonical UUID, while the separate Human Knowledge branch
provides review and explanation evidence without silently creating or replacing identity. The
runtime `hashing-v1` representation is deterministic and hashing-based; it is **not a learned neural
embedding model**. These boundaries are documented in the [MVP evidence](evidence/product-variant-resolver-mvp.md)
and [family-level Human Knowledge evidence](evidence/family-level-human-knowledge-t47.md).

## 2. Current-evidence resume bullets

- Built a confidence-aware product entity-resolution service that combines sparse retrieval, deterministic non-neural `hashing-v1` similarity, structured evidence, RRF fusion, calibration, and abstention; on the frozen 21-case fixture Test (12 matched targets), it achieved Recall@25 `12/12`, Top-1 `12/12`, precision `10/10`, and false matches `0/9`, with fixture-only limitations explicitly retained ([fixture report](../reports/fixture-v1/evaluation-fixture-v1-test.md)).
- Designed a Dual-RAG authority boundary that keeps canonical identity resolution separate from Human Knowledge review evidence: the family-level branch can support typed debug and explanation results, but cannot emit or replace the canonical UUID; the verified 142-document Human Knowledge pool left the frozen canonical evaluation unchanged ([Human Knowledge evidence](evidence/family-level-human-knowledge-t47.md)).
- Built an offline, output-blind canonical-authority workflow with two explicit owner Gates and field-level provenance; it established 20 community-revision-exact variants across seven multi-release families with zero shortfalls, then preserved the original blocked audit beside a new versioned RHB-T4 PASS ([CAR evidence](evidence/canonical-authority-review-v1.md)).
- Authored a private 60-case non-synthetic query artifact through an independently isolated output-blind workflow; Git retains only hashes and safe aggregate counts, while the data Gate remains honestly blocked on five published provisional challenge shortfalls ([RHB-T5 evidence](evidence/representative-hard-benchmark-query-authoring.md)).
- Ran an immutable shadow comparison of RRF, frozen MiniLM pointwise reranking, and a project-trained listwise attention reranker over identical frozen Top-25 candidate pools; all three scored Top-1 `12/12`, while resolver p95 was `1.398 ms`, `89.164 ms`, and `89.583 ms`, so the predeclared selector returned `winner: null` and kept RRF as the runtime default ([comparison report](../reports/neural-reranker-comparison-v1/comparison.md)).

## 3. 60–90 second interview pitch

Marketplace titles are noisy: the same casting can appear with missing years, inconsistent colors,
seller shorthand, or collector numbers that look like quantities. Product Variant Resolver treats
that as confidence-aware entity resolution rather than asking a language model to guess. It extracts
signals, retrieves candidates through sparse search, deterministic non-neural hashing similarity,
and structured evidence, fuses their ranks with RRF, then uses calibration and a decision policy to
return `matched`, `ambiguous`, or `no_match`. I also separated authority between two retrieval
branches: only the canonical catalog can produce a canonical UUID, while Human Knowledge supports
review and explanation without becoming product truth. For model selection, I compared the RRF
baseline against frozen MiniLM pointwise and project-trained listwise rerankers on identical Top-25
candidate pools. All three ranked the 12 matched fixture targets correctly, but neural p95 latency
was about 89 ms versus 1.398 ms for RRF, so the predeclared decision was `winner: null` and RRF stayed
the default ([measured comparison](../reports/neural-reranker-comparison-v1/comparison.md)). The main
limitation is that this is a small, saturated synthetic/curated fixture—not evidence of production
or real-marketplace accuracy—so the next meaningful improvement is a representative hard benchmark,
not more model complexity.

## 4. Claim guardrails

| Topic | Safe current claim | Do not claim | Evidence |
|---|---|---|---|
| Project category | Confidence-aware product entity-resolution system with a Dual-RAG authority boundary | LLM-generated resolver or generative RAG answer system | [MVP evidence](evidence/product-variant-resolver-mvp.md) |
| Similarity representation | `hashing-v1` is a deterministic, hashing-based, non-neural similarity baseline | Neural embedding, MiniLM, Sentence Transformer, or semantic foundation model in the default runtime | [fixture report](../reports/fixture-v1/evaluation-fixture-v1-test.md) |
| Neural models | MiniLM pointwise and the trained listwise head are offline shadow-comparison arms; neither is active in FastAPI | Neural reranking is deployed, promoted, or universally ineffective | [neural evidence](evidence/neural-reranker-comparison-v1.md) |
| Model decision | The frozen comparison returned `winner: null`; RRF remains the runtime default because the neural arms added no Top-1 gain on this Test | RRF is universally superior, or latency alone caused rejection | [comparison report](../reports/neural-reranker-comparison-v1/comparison.md) |
| Evaluation | The checked-in benchmark has 100 synthetic/curated cases, a 120-product fixture catalog, and a 21-case Test with 12 matched ranking targets | Production accuracy, broad marketplace coverage, or statistical generality | [fixture report](../reports/fixture-v1/evaluation-fixture-v1-test.md) |
| Perfect fixture metrics | State the numerator, denominator, fixture scope, and saturation whenever using `1.0`, `100%`, or a perfect count | Unqualified “100% accurate” | [fixture report](../reports/fixture-v1/evaluation-fixture-v1-test.md) |
| Canonical authority | Twenty owner-reviewed variants across seven families are exact relative to one frozen attributed community revision; unsupported color/edition stay null | Mattel/manufacturer certification, global Hot Wheels ground truth, completed real-marketplace benchmark, or RHB-T5 benchmark acceptance | [CAR evidence](evidence/canonical-authority-review-v1.md) |
| RHB-T5 query artifact | Sixty unique non-synthetic queries were authored output-blind and kept local-only; Git has an aggregate-only manifest, and published coverage shortfalls block representative-pilot acceptance | Completed representative benchmark, owner-reviewed labels, Development/Test split, resolver evaluation, or real-marketplace accuracy | [RHB-T5 evidence](evidence/representative-hard-benchmark-query-authoring.md) |

## 5. Future-only metric template

> **FUTURE ONLY — not a current project result.** Use this template only after a representative,
> independently reviewed real-marketplace benchmark has been collected, frozen, and evaluated. Do
> not replace placeholders with values from the current fixture or describe the template as achieved.

```text
Evaluated on [N] representative real-marketplace listings from [source/time scope], with
[N_matched] matched, [N_ambiguous] ambiguous, and [N_no_match] no-match labels reviewed under
[labeling protocol]. The frozen holdout achieved Recall@[K] [value] ([numerator]/[denominator]),
Top-1 [value] ([numerator]/[denominator]), false-match rate [value]
([false matches]/[non-match cases]), and coverage [value] ([correct matches]/[matched cases]) at
the declared operating threshold. At [concurrency/hardware/runtime boundary], `/resolve` p95 was
[value] ms across [N_requests] measured requests. Evidence: [versioned report link].
```

Before using the template, the linked report must disclose provenance, label review, family-safe
splits, hard negatives, missing-data policy, confidence threshold, raw denominators, latency
boundary, and known limitations. Until then, only the current fixture-scoped bullets above are valid.
