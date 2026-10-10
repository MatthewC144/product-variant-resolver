# Domain ranker v2 remediation — Design

Date: 2026-10-09. Mode: Lite / Lean Industrial. Status: **T1 authorized; protocol frozen before
materialization**.

## Overview

V2 treats the T5 null result as a model-development feedback edge, not as permission to tune against
the 30 observed selection cases. The design changes two controlled variables: it obtains a new,
larger exact-release-focused development corpus and replaces independent binary classification with
one pairwise ordering objective. Everything else remains frozen or newly hash-bound before scoring.

```text
new rights/authority Gate
        |
new family/evidence-safe 120 train / 30 validation / 30 selection minimum
        |
query-only frozen Top-25 pools + retrieval-miss audit
        |
evidence-gated same-casting negative triples
        |
one fixed pairwise MiniLM recipe, seeds 17/29
        |
validation-only early stopping
        |
untouched selection generic/domain comparison
        |
selected checkpoint hash OR winner:null
```

## Failure analysis and hypotheses

The following are observations: both v1 seeds produced identical ranking metrics; later epochs
reduced loss while MRR fell; only 67/345 released negatives were same-casting wrong-exact; and
same-family selection accuracy regressed from 41/52 to 40/52. The generic and both domain arms also
exceeded 200 ms p95, so the absolute latency failure is an environment-wide readiness issue rather
than evidence of domain-checkpoint overhead.

The primary hypothesis is that v1's small binary dataset overrepresented broad wrong-release
distinctions and underrepresented ordered comparisons among releases of the same casting. A second
hypothesis is that the same 30 rows serving early stopping and later winner qualification weakened
the independence of the selection claim. Neither hypothesis is accepted as root cause until a new
experiment tests it.

## Data and partition design

V2 needs at least 180 newly admitted catalog-present queries. Connected components use normalized
query duplicates, evidence event, alias, casting family and exact identity. Components are assigned
before model access to a minimum 120 train, 30 validation and 30 selection layout. If component
constraints cannot satisfy these minima, readiness fails rather than splitting a family.

The miner prioritizes same-casting wrong-exact candidates whose year, series, collector number,
series position or toy identifier conflicts with a query-supported target field. Each of at least 60
qualifying train queries needs two such negatives. Ambiguous siblings remain held. Color and edition
remain unavailable unless separately authoritative; missing values cannot create labels.

T1 selects an owner-authored synthetic route over reusing observed marketplace queries. The source
is the frozen 1,763-row community Wiki snapshot, but all 153 identities from the existing positive
dataset are denied before selection. The capacity audit leaves 1,610 rows; 1,041 rows across 269
casting families have at least three exact fields and at least three family releases. Query templates
project only casting, year, series, series position, collector number and toy number. URLs, filenames,
raw fields and collection metadata are excluded. Row-level output remains local-only.

## Training design

The primary arm remains the pinned MiniLM cross-encoder architecture, but it scores a positive and a
negative for the same query and optimizes their score difference with one fixed pairwise logistic or
margin-ranking loss selected before execution. V2 does not conduct an objective tournament. Two
fixed seeds measure optimization stability; early stopping uses validation MRR@10 only.

The generic checkpoint is never trained. It is rescored on identical v2 selection pools only after
all checkpoints, tie rules and gates are frozen. If no domain seed passes, the output is null.

## Latency and environment readiness

V1 measured nearly identical p95 for generic and domain models, around 244 ms, so fine-tuning did not
create the latency excess. V2 keeps the 200 ms product budget. Before training, a benchmark manifest
freezes CPU model, OS, Python, Torch/Transformers versions, thread count, warm-up, batch and
percentile method. Generic must pass the budget in that environment; otherwise work returns to
benchmark/runtime setup without consuming new labels or training a checkpoint.

## Interfaces and artifacts

- `governance.json`: exact new-data hashes, rights, authority, uses and denylist.
- `split-manifest.json`: aggregate connected-component and leakage evidence.
- `candidate-pool-manifest.json`: frozen catalog/retrieval/render/model bindings.
- private `local-v2/`: row membership, pools, scores and diagnostics; default-deny in Git.
- release-gated minimized pairwise triples and safetensors packages.
- aggregate `ranker-selection.json`: generic/domain metrics, gates and winner or null.

## Error handling and testing

Every stage fails closed on hash drift, legacy-holdout intersection, family/evidence leakage,
insufficient exact-release density, generic latency readiness failure, non-finite scores, unsafe
weights or row-level public output. Tests cover partition components, held ambiguity, pairwise loss,
early-stop isolation, target non-injection, metric/tie calculations, artifact tampering and unchanged
FastAPI defaults.

## Non-goals

This draft does not collect data, regenerate T2/T5 artifacts, train a model, calibrate scores, run a
fresh final test, change FastAPI, or activate runtime. Calibration remains downstream of a future
non-null selected checkpoint.
