# Human Knowledge rank-1 anchor confidence — MVP brief

Date: 2026-09-21. Mode: Lite / Lean Industrial. Status: **completed; no policy qualified**.

## Purpose and boundary

Develop admission v4 using public evidence only after private evaluation showed that an unconditional
rank-1 anchor can preserve wrong candidates. Build a separate public pack containing valid noisy
rank-1 anchors and missing-identity hard negatives, then select at most one confidence threshold
without reading private queries, labels, candidates, or case results.

## Requirements

- **HKAC-R1 — Freeze cases before retrieval.** WHEN v4 begins, THE SYSTEM SHALL freeze ten existing
  valid low-coverage rank-1 cases and twelve newly authored missing-identity hard negatives, source
  hashes, labels, ordering, and denominators before any new retrieval.
- **HKAC-R2 — Public-only construction.** Every case SHALL derive from the committed 142-document
  corpus and public development artifacts. Missing identities SHALL be absent from all casting and
  alias identities. Private local-evaluation paths and content SHALL not be read.
- **HKAC-R3 — Once-only collection.** THE SYSTEM SHALL retrieve each of the 22 frozen queries exactly
  once at Top 5 and reuse those raw rows for every configuration.
- **HKAC-R4 — Frozen confidence.** Rank-1 confidence SHALL equal the greater of identity-token
  coverage and bounded character similarity. Ranks 2–5 SHALL retain the selected v3 coverage gate
  of `0.75`; source order SHALL remain unchanged.
- **HKAC-R5 — Fixed grid.** The grid SHALL compare rank-1 thresholds `0`, `0.5`, `0.55`, `0.575`,
  `0.6`, `0.61`, `0.625`, `0.65`, `0.7`, and `0.75`.
- **HKAC-R6 — Regression gates.** An eligible configuration SHALL retain all existing 168 positive
  hits, four merge controls, zero existing governance violations/unrelated results, all 24 prior
  required hits, all ten anchor-positive hits, and zero retrieval errors.
- **HKAC-R7 — Rank-1 safety gate.** An eligible configuration SHALL return no candidate for each of
  the twelve missing-identity hard negatives.
- **HKAC-R8 — Deterministic selection.** Among eligible configurations, THE SYSTEM SHALL minimize
  nonempty hard negatives and then choose the lowest rank-1 threshold.
- **HKAC-R9 — Development only.** A winner SHALL authorize only another newly versioned private
  evaluation. It SHALL NOT modify runtime, API, PostgreSQL, canonical, release, or color behavior.

## Design

`human_knowledge_anchor_confidence_development.py` first materializes an immutable public pack. Ten
positive cases reuse already committed noisy queries whose correct source-rank-1 target has identity
coverage below 0.75. Twelve negative cases name related but corpus-absent castings; since no document
represents that identity, every returned candidate is unsafe for this bounded test.

After the pack is frozen, a second immutable protocol freezes the confidence formula, thresholds,
gates, upstream hashes, and selection rule. One v4 retriever collects the 22 queries. Each setting
also re-scores the existing 223 public rows, so a threshold cannot pass by solving new negatives while
silently losing prior recall. No neural model, dependency, private evidence, or runtime flag is added.

## Tasks

- [x] **HKAC-T1** Build and freeze the 22-case public anchor-confidence pack. _(→R1–R2)_
- [x] **HKAC-T2** Freeze protocol; implement once-only collection, confidence admission, and selection.
  _(→R3–R9)_
- [x] **HKAC-T3** Add pack, policy, privacy, exactly-once, integrity, and artifact tests. _(→R1–R9)_
- [x] **HKAC-T4** Execute once, run QA, document the result and next gate, then push. _(→R1–R9)_

## Acceptance

The step completes when pack and protocol precede retrieval, all configurations reuse one collection,
the result is reproducible, tests pass, and any winner remains development-only.

## Result

The implementation and evidence contract pass, but no threshold passes the frozen product gates.
Thresholds through `0.61` retain all 168 existing positives and all ten low-coverage anchors, while
ten of twelve missing-identity cases still return at least one candidate. At `0.625`, that negative
count remains ten and the policy loses one existing positive plus one anchor positive. Even `0.75`
still returns candidates for four missing identities while preserving only 167/168 existing and
9/10 anchor positives. Therefore the scalar confidence formula is rejected, no private evaluation
is authorized, and runtime remains unchanged.
