# Domain ranker and selective prediction development v1 — Design

Date: 2026-10-09. Mode: Lite / Lean Industrial. Status: **T1, T1A, T2 and T3 complete; T4+ not authorized**.

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
domain MiniLM fine-tuning (safetensors; public only after release Gate)
        |
generic vs domain ranker selection
        |
selected ranker hash freeze
        |
disjoint calibration fit / threshold selection
        |
reliability + risk/coverage + three-state development policy
        |
aggregate report only after a final-execution Gate; runtime HOLD
```

## Data strategy

### Admissible-data Gate

No current row-level source is implicitly admitted for all three ML uses. A versioned governance
artifact must bind dataset hashes and separately permit `mine_negatives`, `fine_tune`,
`calibration_fit`, `threshold_select` and, later, `fresh_final_score`. For T1, the owner selected an
owner-attested exception: this permits bounded development but does not establish independently
verified third-party license or redistribution rights. T1A separately allows release-gated public
hard-negative pairs and safetensors checkpoints; every public package must retain the rights
limitation and pass artifact-specific privacy, license, lineage and integrity checks.

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

### T2 frozen partition and candidate-pool result

T2 admitted only the frozen 100-row positive development subset and formed 100 singleton connected
components. Deterministic salted component ordering assigned 70 rows to `ranker_train` and 30 rows
to `ranker_selection`. The audit found zero cross-partition overlap for normalized query, alias,
evidence event, casting family and exact identity. Although the source file contains all 153 positive
rows and is parsed before filtering, the opened 53-row test subset received zero adaptive use and
zero scoring; the 20-row negative holdout and 52 no-match development rows likewise received zero
ranker scoring.

Candidate retrieval is query-only: sparse, hashing-dense and structured retrievers feed RRF, then
the pinned generic MiniLM scores the returned candidates. Expected identity is observed only after
retrieval to measure a miss and is never passed into or injected into the retriever. All 100 pools
contain exactly 25 candidates; retrieval misses and target injections are both zero. The public
manifest binds catalog, retriever, renderer, implementation code, generic model revision, config and
manifest hashes so the same frozen pools can later support a fair generic/domain comparison.

Row-level partitions and scored pools remain in Git-ignored `local-t2/` artifacts with mode `0600`.
The owner authorization, split manifest and candidate-pool manifest are aggregate-only tracked files
with mode `0644`. Their strict local check can rederive the private and public artifacts; the
public-only check currently validates schema and self-checksums but cannot independently rederive
row-level claims without the private inputs, an explicit deferred assurance gap.

T2 also exposes a later T6 shortfall: after reserving all 100 positive rows for family-disjoint
ranker train/selection, zero catalog-present family-disjoint rows remain for exact-correctness
calibration. This does not block a separately authorized T3 train-only mining run, but T6 must obtain
new admissible calibration positives rather than reuse ranker rows.

## Hard-negative miner

The v1 miner is deterministic and one-shot. For each train query it records at most five negatives
in this order:

1. same casting, wrong exact release;
2. adjacent year, wrong series or wrong identifier;
3. wrong color when color is explicit and authoritative;
4. high generic-MiniLM score;
5. high RRF rank.

The positive is never injected when retrieval misses. Ambiguous siblings are held rather than
forced into binary labels. Candidate-pool scratch, split membership and unrelated source fields
remain local. A minimized versioned hard-negative pair projection may enter Git only through the
named public package path after its pair-release Gate passes; before that Gate, Git receives only
miner version, input hashes, category counts, held counts and retrieval-miss counts.

### T3 frozen mining and release result

T3 ran exactly once over the 70 `ranker_train` queries and the byte-identical T2 Top-25 pool file.
It released 345 binary pairs: 207 adjacent-year/wrong-series-or-identifier, 67 same-casting
wrong-exact, 67 high-generic-score and 4 high-RRF negatives. Sixty-nine queries contributed at
least two defensible negatives against a preregistered minimum of 36, and the per-query maximum is
five. The remaining ambiguity was not converted into convenient labels: 65 same-family candidates
were held, while 45 permanent-holdout identities, 34 ranker-selection identities and 20 candidates
whose target casting was not explicit were excluded or held by the applicable boundary.

The release surface is exactly five files—`pairs.jsonl`, `manifest.json`, `owner-authorization.json`,
`DATA_CARD.md` and `NOTICE.md`—with recursive rejection of every other nested file. The pair bytes
hash to `50f88e73889b31e8f314e93b2cca9e4871934662b5218c6659a72fe06c0ca2ba`; the package hashes to
`89bc430289c36e75c6302e7aa4ecca1889f32df95e5199f61aba1f676b18022a`; and the manifest content
hash is `da5422568c9b0bae6e3d152d66318e251329ca966dbdff078a78029c77a04392`.

The pair projection intentionally reveals training membership because that fact is necessary to
interpret the training artifact. It still excludes selection/final membership, queries from the
opened 53-positive test and 20-negative holdout, and all 52 no-match development rows. Mining and
scoring counts for those four groups are zero. Rights remain
`owner_attested_not_independently_verified`; the labels are relative to the frozen community
catalog and must not be presented as manufacturer/global truth.

The pair-release scanner covers AWS-style credentials, Bearer tokens, `.env` names, path traversal,
local paths, URLs, email/contact material and other PII/secrets. Its numeric detector is scoped to
avoid treating valid 11-digit product barcodes as contact numbers. It scans the final manifest a
second time, applies the legacy-holdout denylist to sanitized content and rejects unexpected files
recursively. These checks close the two issues found during QA/security review: strict MyPy and
rematerialization coverage were added, then the broad nested Git allowlist was replaced by the exact
five-file contract and expanded content scanning.

T3 did not load a trainer or create a checkpoint. Training runs, calibration, final evaluation and
runtime activation remain zero. T4 needs a separate Gate; before it may release a checkpoint, its
Git allowlist must likewise become an exact package-file contract, and every untrusted text field
must remain data rather than being passed to `eval`, a shell or prompt interpolation.

## Domain Pointwise training

The base architecture and tokenizer remain the pinned MiniLM CrossEncoder. The first experiment
uses one binary relevance objective and one fixed recipe; Pairwise/Listwise objective search is
deferred to avoid a small-data model zoo. Early stopping uses ranker-selection MRR@10, never
calibration or holdout metrics. Two fixed seeds test directional stability.

The checkpoint package contains safetensors weights plus a manifest. T1A permits a future public
package only after its model-release Gate verifies license/NOTICE, base revision, training-rights
limitation, secrets/PII scan, lineage, offline loading and denylist isolation. Optimizer state,
pickle-style weights, caches and local scratch remain private. A checkpoint too large for ordinary
Git must use Git LFS or a release asset while the manifest preserves the actual weight SHA-256.

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
- release-gated `hard-negative-pairs.jsonl`: minimum training projection, positive/negative identity
  and text, negative category, label and miner/config/pool hashes; no unrelated raw source fields.
- release-gated safetensors checkpoint package plus `ranker-manifest.json`, model card,
  license/NOTICE and base/data/config/checkpoint lineage.
- `calibration-manifest.json`: frozen ranker, features, methods and fit/selection hashes.
- `policy.json`: thresholds, parent hashes and `runtime_eligible=false`.
- `development-report.json` and Markdown evidence: aggregates, gates, shortfalls and limitations.

### Publication matrix

| Artifact | Publicability | Required Gate |
|---|---|---|
| Versioned row-level hard-negative pairs | Released for frozen v1 package only | T3 pair-release Gate passed |
| Actual `model.safetensors` package | Allowed in future | T4 model-release Gate |
| Split membership and calibration rows | Private | No public route in this milestone |
| Fresh-final aggregate report | Allowed in future | Separate final-execution Gate |
| Fresh-final row-level queries/predictions | Private by default | Separate disclosure Gate |
| Runtime code/config/model manifest | Allowed in future | Separate runtime-activation Gate |
| Public inference endpoint | Not authorized | Separate security/deployment Gate |

Publication permission, release-Gate success, execution and activation are separate booleans. T1A
changes only future publication eligibility; it does not create a final dataset, run final scoring,
activate runtime or change the FastAPI default.

The T3 pair-release Gate has now passed for the single hash-bound five-file package above. This
changes the first matrix row from eligible to released for that version only; it does not authorize
regeneration with different inputs or any T4+ action.

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
- privacy tests enforcing the artifact allowlist, scanning released pairs/checkpoints for forbidden
  fields and rejecting row-level calibration/final content from public artifacts.

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
