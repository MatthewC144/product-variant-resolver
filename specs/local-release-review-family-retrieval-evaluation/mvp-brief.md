# Local release review-family retrieval evaluation — MVP brief

Date: 2026-09-19. Mode: Lite / Lean Industrial. Status: **implemented; evaluation FAIL retained**.

## Purpose and boundary

Evaluate the five private local review-family documents as shadow candidates in the current Human
Knowledge RAG v4 corpus before any runtime integration. The evaluation uses the existing 142
documents plus the five local documents, for 147 competing documents. It does not change the API,
canonical catalog, PostgreSQL, calibration, or runtime knowledge files.

## Requirements

- **LRFE-R1 — Frozen private benchmark.** The query pack and expected labels SHALL remain under the
  ignored local data tree and SHALL be checksum-bound to the five-document projection.
- **LRFE-R2 — Non-exact positives.** The benchmark SHALL contain exactly 15 positive questions,
  three per local family, and no positive query SHALL equal a target casting or alias after
  normalization.
- **LRFE-R3 — Hard negatives.** The benchmark SHALL contain exactly five near-confusable negative
  questions, one forbidding each local family; other legitimate corpus candidates are allowed.
- **LRFE-R4 — Production-shaped shadow corpus.** Retrieval SHALL run the frozen Human Knowledge RAG
  v4 configuration (`character_score_floor=0.5`, `character_rrf_weight=1.0`, 192-dimensional
  `hashing-v1`) over the current 142 documents plus five local candidates.
- **LRFE-R5 — Label separation.** Collection SHALL read only case ID/type/query and SHALL write all
  raw candidate output before expected labels are loaded for scoring. It SHALL execute every query
  exactly once and SHALL not retry failures.
- **LRFE-R6 — Precommitted gates.** Before retrieval, PASS SHALL require positive Recall@5 = 1.0,
  positive Recall@1 >= 0.8, family coverage@5 = 1.0, zero forbidden-family hits among hard
  negatives, and zero retrieval errors.
- **LRFE-R7 — One-shot evidence.** Once raw results exist, rerun SHALL validate existing evidence
  rather than retrieve again. Changed, partial, or tampered inputs/results SHALL fail closed.
- **LRFE-R8 — Private/public split.** Queries, labels, candidate IDs, ranks, and case results SHALL
  remain private. Public output SHALL contain only hashes, aggregate counts/metrics/gates, fixed
  configuration, limitations, verdict, and zero downstream-effect counts.
- **LRFE-R9 — No promotion.** PASS SHALL mean only that these five family documents passed this
  bounded shadow retrieval test. It SHALL NOT automatically load them at runtime or establish
  release/color/canonical correctness.

## Design

`release_casting_review_evaluation.py` builds a temporary in-memory 147-document catalog, reusing
the selected v4 retriever rather than creating a separate scoring algorithm. `collect()` accepts
only the unlabeled query pack. `run()` durably publishes private raw output and only then opens the
separate benchmark to calculate metrics. `check()` recomputes validation and scoring without
calling retrieval.

The hard-negative rule is intentionally narrow: a near-confusable query must not return the
specified new local family in Top 5, but may correctly retrieve another existing document. This
tests accidental overmatching without pretending the small benchmark contains complete truth for
all 142 existing documents.

## Tasks

- [x] **LRFE-T1** Implement private input validation, 147-document shadow catalog, and label-blind
  collection. _(→R1–R5)_
- [x] **LRFE-T2** Implement scoring, fixed gates, one-shot/check behavior, and privacy-safe public
  outputs. _(→R5–R9)_
- [x] **LRFE-T3** Add unit, privacy, tamper, no-retry, label-order, and real-artifact tests.
  _(→R1–R9)_
- [x] **LRFE-T4** Freeze private inputs, run once, verify the repository, and update evidence,
  decision, roadmap, README, and project log. _(→R1–R9)_

## Acceptance

Twenty frozen private cases ran once against 147 shadow documents. All 15 positives were retrieved
in Top 5 and 13 in Top 1, but three forbidden local-family hits occurred in the five hard negatives;
the precommitted verdict is therefore FAIL. Existing runtime files, API behavior, canonical results,
PostgreSQL, and evaluation/calibration artifacts remain unchanged.
