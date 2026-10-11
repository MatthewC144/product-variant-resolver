# Product Variant Resolver — Portfolio Guide

Use this guide to explain the checked-in system and frozen evidence in resume or interview language.
Claims are deliberately bounded: this is a portfolio-grade entity-resolution research/engineering
system, not a deployed marketplace service or manufacturer-certified resolver.

## Positioning

**Headline:** Confidence-Aware Product Entity Resolution & Neural Learning-to-Rank

**One line:** Maps noisy product text to exact releases through hybrid candidate retrieval, neural
reranking, and calibrated abstention.

The project was motivated by identity errors in an earlier screenshot → reverse-image-search →
price-lookup workflow. That is integration context, not this repository's runtime. Product Variant
Resolver begins with noisy product text/evidence and ends at an identity decision.

The two retrieval corpora are best described as **authority-separated dual-corpus retrieval**. Only
the catalog branch can emit a canonical UUID; Human Knowledge provides review and explanation
evidence. No LLM generates the answer.

## Resume bullets

- Built a confidence-aware product entity resolver in Python/FastAPI over a frozen 1,763-release
  third-party catalog; on a one-shot paired Image/Lens and Shopping final test, a MiniLM Pointwise
  cross-encoder improved exact-release Top-1 from `55%` to `64%` and casting Top-1 from `86%` to
  `95%` over RRF (`n=100` source observations from 50 identities).
- Designed output-blind evaluation and a calibrated `matched` / `ambiguous` / `no_match` policy;
  reported zero false matches on a frozen 20-case catalog-relative negative holdout while retaining
  the honest 73.97% abstention limitation instead of tuning on final data.
- Built a governed domain-adaptation pipeline with query-supported hard-negative mining, two-seed
  RankNet fine-tuning, safetensors packaging, and ONNX equivalence/CPU checks; rejected both domain
  checkpoints when the best gain was only +1/30 exact case and missed preregistered gates.

## 60–90 second interview pitch

My earlier livestream price-checking project captured a frame, used reverse image search, cleaned
the returned titles, and sent a keyword to a pricing API. The weak link was identity: aggressive
cleaning could remove useful identifiers, while titles often mixed the correct casting with the
wrong year or release. I built Product Variant Resolver as a standalone confidence-aware entity
resolver rather than using an LLM to generate a nicer keyword.

The pipeline extracts structured clues, retrieves candidates through sparse search, deterministic
hashing similarity, and structured evidence, then combines rankings with RRF. A local MiniLM
Pointwise cross-encoder can reorder the same Top-25 pool. Calibration is separate from ranking, so
the policy can return `ambiguous` or `no_match` instead of treating a high neural score as truth.

On the strongest frozen benchmark—50 held-out identities observed once through Image/Lens and once
through Shopping—Pointwise improved combined exact-release Top-1 from 55% to 64%, casting Top-1
from 86% to 95%, and MRR@10 from 0.722 to 0.792. Recall@25 stayed at 99%; Recall@10 fell one point,
which I report as a trade-off. The result is ranking evidence, not deployment authorization.

I also built hard-negative mining and pairwise domain fine-tuning. One checkpoint improved exact
Top-1 by only one of 30 cases and failed the preregistered gate, so I kept `winner: null`. The same
discipline applies to calibration: the current operating point is too conservative, so the neural
policy remains offline. The project shows both measurable ML value and the engineering judgment to
reject an insufficient model.

## Code-review path

1. Start with the [system overview](architecture/system-overview.md) and explain the separation of
   retrieval, ranking, calibration, and authority.
2. Use the [code tour](CODE-TOUR.md) to walk from `signals.py` through `api.py`.
3. Open the [dual-source final](../data/evaluation/serper-dual-source-evaluation-v1/raw-pointwise-final-test.json)
   and explain the paired denominator and Recall@10 trade-off.
4. Show the [domain-ranker selection](evidence/domain-ranker-v2-selection.md) to discuss hard
   negatives, ONNX equivalence, frozen gates, and `winner: null`.
5. Close with [limitations](LIMITATIONS.md): evidence quality, offline model status, and the blocked
   calibration operating point.

## Claim guardrails

| Topic | Safe claim | Do not claim |
|---|---|---|
| Category | Confidence-aware product entity resolution and learning-to-rank | Generative chatbot or LLM answer system |
| Catalog | Frozen 1,763-release third-party community snapshot | Mattel-certified or globally complete catalog |
| Primary dataset | 150 identities / 300 paired source records, grouped 100/50 by identity | 300 independent products or organic traffic |
| Primary ranking | Exact Top-1 `55% → 64%`, casting `86% → 95%`, MRR@10 `0.722 → 0.792` | Runtime-policy accuracy or universal superiority |
| Denominator | 100 final source observations from 50 identities | 100 independent final products |
| Similarity baseline | `hashing-v1` is deterministic and non-neural | Learned semantic embedding model |
| Pointwise/Listwise | Offline reranking experiments over a frozen Top-25 pool | Active default FastAPI neural ranking |
| Domain adaptation | Reproducible pairwise experiment; neither checkpoint qualified | Fine-tuning is deployed or clearly superior |
| Calibration | Conservative abstention evidence; no qualifying new policy | High-coverage or runtime-ready selective prediction |
| Human Knowledge | Supporting review/explanation evidence | Canonical identity authority |
| Exact authority | 20 releases relative to one frozen community revision | Manufacturer/global truth |
| PostgreSQL/pgvector | Optional tested retrieval/storage infrastructure | Production-scale deployment proof |

Evidence links and the result hierarchy are maintained in [Results](RESULTS.md). Use
[Known Limitations](LIMITATIONS.md) as the canonical public scope statement.

## Technical stack

| Component | Role |
|---|---|
| Python 3.12 + Pydantic | Typed identity, policy, and evidence contracts |
| FastAPI | Fail-closed `/resolve` and `/health` interfaces |
| Sparse + hashing similarity + structured evidence | High-recall candidate generation |
| RRF | Score-scale-independent rank fusion |
| MiniLM Pointwise cross-encoder | Fine-grained query/candidate reranking |
| RankNet pairwise fine-tuning | Hard-negative domain-adaptation experiment |
| Calibration + abstention | Separate correctness confidence from relevance score |
| ONNX Runtime | Equivalent and faster CPU experiment substrate |
| PostgreSQL + pgvector | Optional persistence and retrieval profile |
| Pytest, Ruff, MyPy | Regression, integrity, and active-core quality gates |

## Honest close

The strongest result is a nine-point exact-release ranking gain, not “100% accuracy.” Query data is
search-result-derived, the catalog is community-maintained, and the current calibrated policy does
not have useful enough coverage for runtime. Present the system as an evidence-driven AI engineering
project with explicit abstention and authority boundaries—not as a deployed marketplace product.
