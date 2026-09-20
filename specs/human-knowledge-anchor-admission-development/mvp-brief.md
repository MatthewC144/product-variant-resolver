# Human Knowledge anchored compatibility admission — MVP brief

Date: 2026-09-20. Mode: Lite / Lean Industrial. Status: **implemented; qualified for new private gate**.

## Purpose and boundary

Develop admission v3 after v2 proved that reordering a sparse candidate pool cannot remove unsafe
neighbors from Top 5. Preserve the source rank-1 anchor, require explicit identity compatibility for
secondary candidates, and select at most one development policy without reading the immutable
private local-family evaluation or changing runtime.

## Requirements

- **HKAA-R1 — Freeze before v3 scoring.** WHEN v3 starts, THE SYSTEM SHALL freeze the upstream v2
  report hash, eight thresholds, anchored-admission rule, gates, and winner ordering before writing
  any v3 result.
- **HKAA-R2 — Public development only.** Scoring SHALL use exactly the validated v2 evidence for the
  committed 199 existing and 24 false-positive development cases; it SHALL NOT read private local
  projection or private evaluation artifacts.
- **HKAA-R3 — No new retrieval.** THE SYSTEM SHALL reuse the validated v2 raw pools and execute zero
  retrieval calls.
- **HKAA-R4 — Anchored compatibility admission.** Source rank 1 SHALL always be admitted. Source
  ranks 2–5 SHALL be admitted only when identity-token coverage meets the configured threshold.
  Source order SHALL remain unchanged and candidates beyond source rank 5 SHALL not enter output.
- **HKAA-R5 — Frozen grid.** THE SYSTEM SHALL compare secondary coverage thresholds `0`, `1/3`,
  `0.4`, `0.5`, `0.6`, `2/3`, `0.75`, and `1.0`.
- **HKAA-R6 — Recall/governance gates.** An eligible configuration SHALL retain all 168 existing
  positive family hits, all four merge controls, zero existing held-family violations, zero unrelated
  nonempty results, all 24 new required hits, and zero upstream retrieval errors.
- **HKAA-R7 — Deterministic selection.** Among eligible configurations, THE SYSTEM SHALL minimize
  new forbidden-hit cases and then choose the lowest secondary threshold.
- **HKAA-R8 — Evidence integrity.** Upstream bytes, admitted ranks, abstention counts, per-case
  outcomes, gates, and winner SHALL be reproducible; check mode SHALL not retrieve or rewrite.
- **HKAA-R9 — Evaluation gate only.** A qualifying winner SHALL only authorize a new versioned
  private shadow evaluation. It SHALL NOT activate API/runtime, PostgreSQL, canonical, release, or
  color behavior.

## Design

`human_knowledge_anchor_admission_development.py` validates the immutable v2 protocol and selection
report, then applies the v3 grid offline. Rank 1 is an anchor because all 24 public safety queries put
their required target first, while v1 showed that globally filtering low-coverage first results can
delete valid typo candidates. Secondary candidates must independently justify their identity-token
compatibility; this introduces the admission/abstention decision missing from pure reranking.

The grid includes the zero-threshold baseline and bounded coverage thresholds already defined by the
same frozen identity matcher. It adds no model, dependency, retrieval call, or runtime flag. A public
development winner remains provisional until it passes a newly frozen private shadow evaluation.

## Tasks

- [x] **HKAA-T1** Implement and freeze the v2-bound anchored-admission protocol. _(→R1–R5)_
- [x] **HKAA-T2** Implement offline scoring, gates, deterministic selection, and reports. _(→R3–R9)_
- [x] **HKAA-T3** Add anchor, threshold, ordering, integrity, privacy, and artifact tests. _(→R1–R9)_
- [x] **HKAA-T4** Execute, run QA, document whether v3 qualifies for a new private gate, and push.
  _(→R1–R9)_

## Acceptance

The protocol preceded v3 scoring and no retrieval was executed. `secondary-075` preserves 168/168
old positives and 24/24 new required targets while reducing forbidden cases from 18/24 to 0/24. It
qualifies only for a newly versioned private shadow evaluation; runtime remains unchanged.
