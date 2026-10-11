# Serper dual-source four-arm evaluation v1 — MVP brief

Date: 2026-10-10. Mode: Lite / Lean Industrial. Status: **complete**.

## Purpose

Compare resolver behavior fairly across four query arms from the frozen 300-row benchmark:
image-search raw, image-search cleaned, Shopping raw, and Shopping cleaned. Freeze a grouped,
year-stratified 100-target development / 50-target test split before any resolver output is read.

## Observable requirements

- **SDSE-R1 — Dataset pin.** WHEN the benchmark is loaded, THE SYSTEM SHALL require dataset SHA-256
  `05213c4c8d101d844b179359aef63264b8579c2f728b14f5adbe7a3a75a56034`, 150 targets, 300 rows,
  the frozen catalog binding and the exact minimal schema.
- **SDSE-R2 — Pair safety.** WHEN a split is built, BOTH source records for one `target_id` SHALL be
  assigned together; development and test SHALL be disjoint and exhaustive.
- **SDSE-R3 — Year stratification.** WHEN the 100/50 split is built, THE SYSTEM SHALL allocate each
  release year proportionally, then deterministically rank targets inside the year using a
  versioned SHA-256 salt.
- **SDSE-R4 — Test isolation.** WHILE metrics or policies are developed, default evaluation SHALL
  read development only. Test requires a later explicit one-time authorization.
- **SDSE-R5 — Four-arm symmetry.** WHEN evaluation is implemented, all four arms SHALL use identical
  candidates, resolver configuration, target membership and metrics; only query text may differ.
- **SDSE-R6 — No collection artifact expansion.** THE SYSTEM SHALL NOT add URLs, images, provider
  payloads, split fields or a second row-level assignment file to the final dataset directory.
- **SDSE-R7 — Aggregate reporting.** Reports SHALL contain aggregate counts and metrics only, retain
  the catalog-relative authority disclaimer, and SHALL NOT persist row-level predictions.
- **SDSE-R8 — Pointwise isolation.** WHEN Pointwise is compared on development, THE SYSTEM SHALL
  use raw queries only, reuse the exact RRF Top-25 membership, validate the frozen local model and
  prior winner binding, reproduce the frozen RRF baseline, and SHALL NOT score policy or test.
- **SDSE-R9 — One-shot final.** WHEN the owner authorizes SDSE-T4, THE SYSTEM SHALL score each of
  the 50 frozen test targets exactly once per source with the preselected raw + Pointwise path,
  publish aggregate-only results, prohibit reruns and SHALL NOT adapt model, candidates or policy.

## Design

```text
frozen 150-target / 300-row dataset
  -> strict paired schema + exact dataset SHA check
  -> group by target_id
  -> stratify by release_year
  -> deterministic salted SHA-256 order inside each year
  -> 100 development targets / 50 untouched test targets
  -> symmetric four-arm development evaluation
  -> frozen aggregate baseline; test remains unopened
  -> raw-only RRF versus frozen Pointwise ranking ablation
  -> select development ranker; test remains unopened
  -> explicit owner gate
  -> one aggregate-only final test; rerun prohibited
```

The split is frozen as code constants plus an assignment SHA-256. No row-level manifest is written.
The proportional allocation is 2023/2024/2025/2026 development `26/22/30/22` and test
`13/11/15/11`. This uses labels only for pre-evaluation stratification and does not inspect resolver
predictions or errors.

## Tasks

- [x] **SDSE-T1** Implement strict dataset loading and freeze the grouped, year-stratified 100/50
  split without opening test outputs. _(→SDSE-R1–R4,R6–R7)_
- [x] **SDSE-T2** Implement aggregate development-only evaluation for all four symmetric arms.
  _(→SDSE-R4–R7)_
- [x] **SDSE-T3** Run development-only baseline, compare raw versus cleaned effects and freeze the
  next model/policy decision without consulting test. _(→SDSE-R4–R7)_
- [x] **SDSE-T3A** Compare frozen neural Pointwise versus reproduced RRF on the two raw development
  arms, then freeze the ranker decision without policy scoring or test access. _(→SDSE-R4,R7–R8)_
- [x] **SDSE-T4** After an explicit owner gate, run one untouched 50-target test evaluation and
  publish aggregate results only. _(→SDSE-R4,R7–R9)_

## Acceptance for T1

The exact dataset validates as 150 complete pairs and 300 records; the frozen split contains 100
development and 50 test target IDs, represents 200/100 records, has zero pair leakage, preserves the
expected year allocation and reproduces assignment SHA-256
`4831d72b8b5ced2550e1dc1c35498781279d6e1ea866c4b3669638035b73ef13`. The dataset directory still
contains only `dataset.json`; resolver evaluation has not run.

## T3 development baseline decision

The four arms were each evaluated once on the same 100 development targets with the frozen
1,763-candidate catalog, offline RRF retrieval, 192-dimensional hashing embeddings,
`candidate_limit=25` and reranking disabled. The aggregate artifact is
`data/evaluation/serper-dual-source-evaluation-v1/development-baseline.json`, SHA-256
`8ffb7758fd344bc632747432be1232efed49cbf8155721867bb747086481932c`.

| Development arm | Casting Top-1 | Exact-release Top-1 | Recall@10 | Recall@25 | MRR@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Image raw | 88% | 39% | 93% | 99% | 0.586 |
| Image cleaned | 80% | 33% | 91% | 93% | 0.534 |
| Shopping raw | 95% | 57% | 100% | 100% | 0.750 |
| Shopping cleaned | 84% | 51% | 96% | 98% | 0.691 |

Cleaning reduced casting Top-1 by 8 percentage points for image search and 11 points for Shopping;
it reduced exact-release Top-1 by 6 points for both sources. Therefore raw text is frozen as the
primary representation for both sources, cleaned text remains an ablation only, and Shopping raw is
the current development leader. The next development experiment may compare the already frozen
Pointwise reranker on the two raw arms only. This decision does not activate runtime behavior, retune
thresholds or authorize SDSE-T4; the 50 test targets still have zero scored outputs.

## T3A raw-only Pointwise decision

The frozen local `cross-encoder/ms-marco-MiniLM-L6-v2` revision
`233902d25c440f23af6f7d6e94d2946bac0bee0a` reranked each raw query's unchanged RRF Top-25.
The model was not refit on this dataset. The aggregate artifact is
`data/evaluation/serper-dual-source-evaluation-v1/raw-pointwise-development.json`, SHA-256
`f760d733ecc6cbee2124d42ad539d81b2f810bff2842ee26b2a2e6b2946df362`.

| Development source | Ranker | Casting Top-1 | Exact-release Top-1 | Recall@10 | Recall@25 | MRR@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Image raw | RRF | 88% | 39% | 93% | 99% | 0.586 |
| Image raw | Pointwise | **98%** | **48%** | **97%** | 99% | **0.676** |
| Shopping raw | RRF | 95% | 57% | 100% | 100% | 0.750 |
| Shopping raw | Pointwise | **99%** | **74%** | 100% | 100% | **0.848** |

Pointwise improved exact-release Top-1 by 9 percentage points for image search and 17 points for
Shopping, while preserving candidate membership and Recall@25. It is therefore selected as the
development ranking winner over RRF for both raw sources. This selects only ranking order: no
calibration, three-state policy, threshold or runtime behavior was evaluated or activated. The
50-target test still has zero scored outputs and requires the separate SDSE-T4 owner gate.

## T4 one-shot final test

The project owner authorized SDSE-T4 after the exact raw + Pointwise boundary was presented. The
authorization SHA-256 is
`b22e32384961d0f5be469baa641bbdab7be6393dbbf74484a48cfce097fcfc14`. The one final test run used
all 50 previously unopened targets per source and produced aggregate artifact
`data/evaluation/serper-dual-source-evaluation-v1/raw-pointwise-final-test.json`, SHA-256
`ba06ef6db36e86d436205af82b7d96f2af902c4f082194acfe006af470ba37e2`.

| Final-test source | Ranker | Casting Top-1 | Exact-release Top-1 | Recall@10 | Recall@25 | MRR@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Image raw | RRF | 80% | 50% | 98% | 98% | 0.690 |
| Image raw | Pointwise | **92%** | **56%** | 96% | 98% | **0.744** |
| Shopping raw | RRF | 92% | 60% | 100% | 100% | 0.754 |
| Shopping raw | Pointwise | **98%** | **72%** | 100% | 100% | **0.841** |

Across both sources, Pointwise improved casting Top-1 from 86% to 95%, exact-release Top-1 from
55% to 64%, and MRR@10 from 0.722 to 0.792. Combined Recall@25 stayed at 99%; combined Recall@10
decreased from 99% to 98% because Image fell from 98% to 96%. The final result therefore confirms
the preselected Pointwise Top-1/MRR advantage while disclosing its small Image Recall@10 tradeoff.
No calibration/policy claim or runtime activation follows from this ranking-only result, and the
one-shot guard now rejects another test execution before loading data or models.
