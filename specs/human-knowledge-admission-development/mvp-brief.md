# Human Knowledge admission-policy development — MVP brief

Date: 2026-09-20. Mode: Lite / Lean Industrial. Status: **implemented; no mitigation qualified**.

## Purpose and boundary

Compare a frozen grid of post-retrieval identity-token coverage filters using only development data:
the existing 199-case positive/governance pack and the new 24-case required/forbidden pack. Select at
most one experimental policy without changing runtime or reading the private local-family test set.

## Requirements

- **HKAD-R1 — Frozen protocol.** WHEN development begins, THE SYSTEM SHALL freeze source hashes,
  token-match semantics, five coverage thresholds, gates, and deterministic winner ordering before
  any grid result is written.
- **HKAD-R2 — Development-only inputs.** Collection SHALL use exactly the committed 142-document
  corpus, 199-case existing development pack, and 24-case false-positive development pack; it SHALL
  NOT open local private projection/evaluation artifacts.
- **HKAD-R3 — Bounded token alignment.** Candidate identity coverage SHALL be computed only from
  `casting` and approved `aliases` after the existing identity-core noise policy, using exact,
  compact, two-character-or-longer prefix abbreviation, numeric suffix, or SequenceMatcher >= 0.8.
- **HKAD-R4 — Fixed grid.** The grid SHALL contain baseline thresholds 0.0, 0.5, 2/3, 0.75, and 1.0.
  All settings SHALL filter the same once-collected Top-5 candidate lists.
- **HKAD-R5 — Recall/governance gates.** An eligible policy SHALL retain all 168 existing positive
  family hits, all four merge controls, zero existing held-family violations, zero unrelated nonempty
  results, all 24 new required hits, and zero retrieval errors.
- **HKAD-R6 — Deterministic selection.** Among eligible policies, THE SYSTEM SHALL minimize new
  forbidden-hit cases and then choose the lowest threshold. IF none is eligible, no winner SHALL be
  selected.
- **HKAD-R7 — Evidence integrity.** Raw candidate IDs, coverage values, per-configuration case ranks,
  summaries, gates, and winner SHALL be reproducible and source-bound; check mode SHALL never retrieve.
- **HKAD-R8 — Experimental-only output.** A selected winner SHALL remain a development artifact and
  SHALL NOT modify `HumanKnowledgeIdentityRetriever`, API settings, PostgreSQL, canonical truth, or
  the private evaluation.

## Design

`human_knowledge_admission_development.py` validates both committed development packs, creates one
current v4 retriever over 142 documents, and retrieves each of the 223 queries once at Top 5. It then
computes maximum candidate identity-token coverage and applies every frozen threshold to the same raw
rows. This isolates policy differences from retrieval timing or repeated-call variation.

Coverage operates on candidate identity tokens, not generic searchable metadata. A candidate token
matches a query token by exact equality, compact containment, prefix abbreviation of at least two
characters, numeric suffix equivalence, or SequenceMatcher ratio >= 0.8. The initial grid is small to
keep Lite-mode evidence interpretable; no neural model or new dependency is introduced.

## Tasks

- [x] **HKAD-T1** Implement and freeze protocol, token alignment, grid, and input integrity checks.
  _(→R1–R4)_
- [x] **HKAD-T2** Implement once-only collection, scoring, gates, selection, and deterministic report.
  _(→R4–R8)_
- [x] **HKAD-T3** Add unit, selection, no-private-input, exactly-once, tamper, and artifact tests.
  _(→R1–R8)_
- [x] **HKAD-T4** Execute the grid, run QA, document result and remaining project work, then push.
  _(→R1–R8)_

## Acceptance

All five configurations were scored from one 223-query raw collection. The four nonzero filters
reduced forbidden cases from 18 to 7/2/0/0, but each violated at least one frozen recall gate. The
algorithm therefore falls back to baseline; no mitigation qualified and runtime remains unchanged.
