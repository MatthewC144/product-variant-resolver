# Domain ranker v2 remediation — Design

Date: 2026-10-10. Mode: Lite / Lean Industrial. Status: **T0–T5 complete; T6+ not authorized**.

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

T1 materialized three aggregate-only public artifacts: Owner authorization, authoring protocol and
effective governance. The governance code is bound to commit
`819666fad6756e06d695af2dadfab833fa7f17fc`; source and denylist inputs are hash-bound. The effective
permissions allow only a future local authoring step after a separate T2 Gate. Candidate scoring,
mining, training, calibration, final evaluation, row-level publication and runtime all remain false.

T2 uses one deterministic target per selected casting family. Families are ordered by the T1 salted
SHA-256 rule; a second fixed salt chooses one release inside each family, and a third fixed salt
chooses one of the three frozen query templates. The first 120 families become train, the next 30
validation and the final 30 untouched selection. This deliberately stronger one-family-per-query
rule makes cross-partition casting leakage impossible and preserves at least two unused same-family
siblings for every row, without yet assigning any negative label.

The resulting local query pack is content-addressed and stored with mode `0600`. Public query and
split manifests expose only totals, template distribution, lineage hashes and overlap counts. They
do not contain queries, expected identities, case IDs or split membership. T2 does not build the
Top-25 pools; retrieval and latency readiness belong to T3.

T3 rebuilds the frozen 1,763-release evaluation catalog and runs sparse, 192-dimensional hashing
dense and structured retrieval with RRF `k=60`. Retrieval receives only query-derived signals;
expected identity is joined afterward solely to count misses and is never inserted into a pool. The
pinned generic `cross-encoder/ms-marco-MiniLM-L6-v2` revision scores all frozen candidates once.
Latency is measured separately on validation only, with one CPU thread, batch size 25, three warm-up
runs and 90 timed pool calls. No selection quality metric is computed.

T3 produced all 180 pools and the query-only retrieval contract had zero misses, but the pinned
generic PyTorch/Sentence Transformers execution path measured p95 `217.699834 ms`. The failure is
about inference readiness, not retrieval correctness or domain-model quality. A repair iteration may
evaluate one preregistered CPU inference implementation while keeping model weights, tokenizer,
max-length, batch, inputs and score ordering unchanged. It must not lower the 200 ms budget or use
selection quality to choose an optimization.

T3R uses ONNX Runtime `CPUExecutionProvider` with a float32 opset-17 graph, one intra-op thread, one
inter-op thread, sequential execution and all graph optimizations. Diagnostic validation rejected
direct Transformers and SDPA because neither materially improved latency. It also rejected dynamic
INT8: although smaller and faster, only 3/180 complete candidate orderings remained identical. The
float32 ONNX route preserved 180/180 ordering with a diagnostic maximum logit delta around `1.5e-5`
and crossed the latency budget. Formal output must reproduce those preregistered equivalence gates.
The 91 MB graph remains reconstructible local state rather than adding a large binary to Git.

The formal run reproduced deterministic graph bytes and passed equivalence before timing. ONNX
Runtime p95 was `103.654042 ms`, compared with T3 PyTorch p95 `217.699834 ms`; the frozen 200 ms
budget therefore passes without changing model weights, pool membership or ordering. This approves
the inference substrate for the experiment only—it does not activate ONNX in FastAPI or authorize
T4 labels/training.

T4 parses only the 120 train rows. For each row, it first verifies that the target UUID is uniquely
present and that the rendered target exactly matches the frozen casting, year, series, series
position, collector number and toy number. It then considers only same-normalized-casting siblings.
The frozen query template determines which exact fields are allowed to establish a conflict: year,
toy number and collector number for the two identifier templates; year, series, series position and
collector number for the series template. Missing values do not conflict, and score/rank is never
label authority. A row enters training only with at least two defensible siblings; all defensible
siblings for an admitted row become triples, while ambiguous siblings and one-negative rows are
retained as held audit records.

This yields 112 admitted train queries and 332 triples. Eight train queries have only one defensible
sibling; their eight candidates remain held. Nineteen additional same-casting siblings have no
query-supported exact conflict and also remain held. This is intentionally stricter than treating
every different UUID as negative: a UUID difference proves a different catalog row, not that the
query contains enough information to prefer one release. Validation and selection rows are not used
for mining.

## Training design

The primary arm remains the pinned MiniLM cross-encoder architecture. For each batch, it scores the
positive and negative for the same query in one forward input and minimizes
`mean(softplus(-(positive_logit-negative_logit)))`. This RankNet-style logistic objective directly
penalizes an incorrect within-query ordering without imposing an arbitrary fixed margin. V2 does not
conduct an objective tournament.

The preregistered recipe uses seeds 17/29, triple batch size 8 (16 query/candidate forwards),
learning rate `1e-5`, AdamW weight decay `0.01`, 10% linear warm-up then linear decay, maximum length
128, gradient clip 1.0, at most four epochs and patience two. After every epoch, only validation
MRR@10 is computed; ties retain the earliest epoch. Training state stays float32 and the best
checkpoint per seed is released as float16 safetensors. Optimizer/scheduler state and pickle formats
are never published.

The generic checkpoint is never trained. It is rescored on identical v2 selection pools only after
all checkpoints, tie rules and gates are frozen. If no domain seed passes, the output is null.

The formal T5 run preserved that boundary. Seed 17 validation MRR@10 moved `0.9333 → 0.95 → 0.95
→ 0.95`, selecting epoch 2; seed 29 moved `0.9333 → 0.9333 → 0.95 → 0.95`, selecting epoch 3.
Pairwise loss continued falling after the selected epochs, but ties retained the earlier checkpoint.
This prevents lower training loss from being mistaken for better validation ranking. Both artifacts
remain candidates only; the generic/domain comparison belongs exclusively to T6.

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
- private `local-t2/`, `local-t3/` and `local-t4/`: row membership, pools, triples and held audit
  records; default-deny in Git and mode `0600`.
- release-gated minimized pairwise triples and safetensors packages.
- public `artifacts/domain-ranker-v2-remediation/checkpoint-v1/`: two allowlisted float16
  safetensors checkpoints, tokenizer/configs, lineage, license, notice and model card.
- aggregate `ranker-selection.json`: generic/domain metrics, gates and winner or null.

## T6 frozen selection protocol

T6 reuses the v1 product gates without relaxing them after observing v2 output: exact-release
Top-1 must improve by at least 3/30, MRR@10 by `0.02`, and same-family accuracy by `0.10`; casting
Top-1 may lose at most one case, Recall@25 may not fall, CPU p95 must remain at most `1.25x` generic
and at most `200 ms`, and both seeds must move exact Top-1 and MRR in the positive direction. A
checkpoint must pass every check. Eligible ties resolve by exact Top-1, MRR@10, same-family
accuracy, lower p95 and then lower seed. Otherwise the output is `winner: null`.

Latency is compared on one inference substrate: generic uses the already verified float32 ONNX
graph; each immutable T5 checkpoint is converted to a local-only float32 ONNX graph. Before its
quality metrics are accepted, every domain graph must stay within `2e-5` of PyTorch logits and
preserve the complete Top-25 ordering on all 30 selection pools. Each arm then uses one CPU thread,
batch 25, three warm-ups and 90 timed pool calls. This prevents framework overhead from deciding
the model winner. The one-shot runner refuses to overwrite any existing T6 artifact.

## Error handling and testing

Every stage fails closed on hash drift, legacy-holdout intersection, family/evidence leakage,
insufficient exact-release density, generic latency readiness failure, non-finite scores, unsafe
weights or row-level public output. Tests cover partition components, held ambiguity, pairwise loss,
early-stop isolation, target non-injection, metric/tie calculations, artifact tampering and unchanged
FastAPI defaults.

## Non-goals

T5 does not regenerate v1/T2 sources, inspect v2 selection quality, compare generic/domain winners,
calibrate scores, run a fresh final test, change FastAPI, or activate runtime. Calibration remains
downstream of a future non-null selected checkpoint.
