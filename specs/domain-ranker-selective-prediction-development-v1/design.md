# Domain ranker and selective prediction development v1 — Design

Date: 2026-10-09. Mode: Lite / Lean Industrial. Status: **T1 approved; T2+ pending owner Gates**.

## Overview

The milestone treats hard-negative mining, domain cross-encoder fine-tuning and calibration as one
ordered ML system. Mining defines what the ranker learns; the frozen ranker defines the score
distribution; calibration then converts that distribution into correctness/no-match evidence; the
policy converts evidence into `matched`, `ambiguous` or `no_match`.

```text
rights + label-authority Gate
        |
family/evidence-safe development split + permanent holdout denylist
        |
frozen generic MiniLM/RRF Top-25 pools
        |
train-only one-shot hard-negative mining
        |
domain MiniLM fine-tuning (local safetensors)
        |
generic vs domain ranker selection
        |
selected ranker hash freeze
        |
disjoint calibration fit / threshold selection
        |
reliability + risk/coverage + three-state development policy
        |
aggregate-only report; runtime HOLD; no final test
```

## Data strategy

### Admissible-data Gate

No current row-level source is implicitly admitted for all three ML uses. A versioned governance
artifact must bind dataset hashes and separately permit `mine_negatives`, `fine_tune`,
`calibration_fit`, `threshold_select` and, later, `fresh_final_score`. For T1, the owner selected a
local-only, owner-attested exception: this permits bounded local development but does not establish
independently verified third-party license or redistribution rights. Raw rows, pairs and checkpoints
therefore remain Git-ignored, and public weights remain prohibited.

Two safe routes are supported:

1. **Rights-cleared existing development route.** Admit only specific existing development rows
   after purpose expansion and rights evidence; permanently exclude the opened 53/20 holdouts.
2. **Owner-authored/synthetic route.** Build a new local-only development pack from owner-authored
   queries and project-controlled synthetic corruptions. This proves the pipeline but must not be
   marketed as representative marketplace generalization.

If neither route yields at least 50 usable ranker-training queries, 15 ranker-selection queries and
two defensible hard negatives for most train queries, the milestone stops at data readiness.

### Partition isolation

Connected components are formed from normalized query duplicates, source/evidence events, casting
families, aliases and exact release identities. Components, rather than individual rows, are placed
into ranker train/selection and calibration fit/selection. The future final partition lives outside
the trainer-readable tree and is not created or mounted in this milestone.

## Hard-negative miner

The v1 miner is deterministic and one-shot. For each train query it records at most five negatives
in this order:

1. same casting, wrong exact release;
2. adjacent year, wrong series or wrong identifier;
3. wrong color when color is explicit and authoritative;
4. high generic-MiniLM score;
5. high RRF rank.

The positive is never injected when retrieval misses. Ambiguous siblings are held rather than
forced into binary labels. Row-level pools remain local; Git receives miner version, input hashes,
category counts, held counts and retrieval-miss counts only.

## Domain Pointwise training

The base architecture and tokenizer remain the pinned MiniLM CrossEncoder. The first experiment
uses one binary relevance objective and one fixed recipe; Pairwise/Listwise objective search is
deferred to avoid a small-data model zoo. Early stopping uses ranker-selection MRR@10, never
calibration or holdout metrics. Two fixed seeds test directional stability.

The local checkpoint package contains safetensors weights plus a manifest. It is Git-ignored. A
public manifest can be committed only if it contains no row-level content and model/data rights
allow disclosure of hashes and aggregates. Public weights require a separate redistribution and
memorization Gate.

## Calibration and policy

Calibration starts only after the winner is frozen. The minimum interface remains five features:

```text
top1 active-ranker score
top1 - top2 margin
retrieval-source support
structured match count
structured conflict count
```

The primary exact-correctness arm is the existing five-feature logistic form. A single-score Platt
baseline and single-parameter temperature baseline may be compared on the same frozen scores.
Isotonic is deferred unless calibration-fit contains at least 200 independent groups and sufficient
score diversity.

Low `P(exact-correct)` is not automatically `P(no_match)`. If rights-cleared no-match development
rows are available, a separate `p_absent` head is fit; otherwise v1 may select only matched versus
ambiguous and must leave `no_match` unchanged/unsupported rather than infer absence from low
correctness.

The decision policy uses frozen match/no-match precision, recall, false-decision and coverage gates.
It remains development-only and `runtime_eligible=false`.

## Interfaces and artifacts

- `governance.json`: allowed dataset hashes, uses, authority wording, publication scope and denylist.
- `split-manifest.json`: non-reversible group/partition hashes and leakage-scan aggregates.
- `candidate-pool-manifest.json`: catalog/retriever/renderer/model/Top-K hashes.
- local `hard-negative-pool.json`: approved train rows and negative categories.
- local checkpoint plus public `ranker-manifest.json`: base/data/config/checkpoint lineage.
- `calibration-manifest.json`: frozen ranker, features, methods and fit/selection hashes.
- `policy.json`: thresholds, parent hashes and `runtime_eligible=false`.
- `development-report.json` and Markdown evidence: aggregates, gates, shortfalls and limitations.

## Error handling and safety

The pipeline fails closed before training or artifact writes on authorization drift, rights gaps,
legacy-holdout intersection, family/evidence leakage, hash drift, unsafe model files, non-finite
scores, missing authority, PII findings or checkpoint/feature mismatch. Raw text is treated as data,
normalized and length-bounded, and never interpreted as code, paths or instructions.

## Testing strategy

- contract tests for permissions, hashes, schemas and holdout denylist;
- leakage tests for duplicate, alias, evidence-event and family intersections;
- hand-computed miner fixtures for negative categories, ambiguity and retrieval misses;
- deterministic training smoke tests with tiny synthetic data plus two-seed integration checks;
- safetensors, offline-load and manifest-tamper tests;
- metric tests for Top-1, MRR, Brier, NLL, ECE bins, reliability, AURC and risk/coverage;
- regression tests proving FastAPI defaults, catalog and opened holdout artifacts do not change;
- privacy tests recursively rejecting row-level query/candidate/prediction content from public JSON.

## Stop conditions

- missing rights, training-use authorization or exact/source-relative label authority;
- any legacy 53/20 record or hash reaches an adaptive phase;
- insufficient usable queries or defensible hard negatives;
- retrieval misses exceed 5% in admitted development data;
- ranker gate fails, latency exceeds budget or seeds disagree in improvement direction;
- calibration does not improve Brier without worsening NLL/ECE;
- no selective operating point meets the frozen safety/coverage gates;
- no fresh final dataset exists: runtime and new portfolio headline remain blocked regardless of
  development performance.
