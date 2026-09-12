# Human Knowledge Retriever Redesign — Lite Specification Evidence

> Date: 2026-09-12
>
> Mode: Lite / Lean Industrial
>
> Status: Proposed; implementation awaits project-owner confirmation

## Trigger and evidence boundary

The frozen Human Knowledge RAG v2 evaluation passed eight of nine gates but failed lexical-
variation Recall@5 at `31/42 = 0.7381` against `>=0.75`. All eleven positive errors were lexical:
ten returned other candidates and one returned none. The v1 result is now development-known, so it
is retained only as the problem diagnosis and cannot select v3 parameters or serve as final evidence
for a changed retriever.

The proposed feature is documented in:

- `specs/human-knowledge-retriever-redesign/requirements.md` — HRR-R1–HRR-R20.
- `specs/human-knowledge-retriever-redesign/design.md` — character index, hybrid fusion,
  selection, runtime/API, final evaluation, and safety design.
- `specs/human-knowledge-retriever-redesign/tasks.md` — six ordered, independently verifiable
  delivery stages with two explicit owner gates.

No source code, runtime setting, query dataset, model artifact, retrieval output, canonical file,
PostgreSQL row, or final-evaluation claim was created in this specification task.

## Selected technical direction

The design proposes `human-knowledge-hybrid-v3`: retain the existing sparse and deterministic
`hashing-v1` dense sources, then add a dependency-free character n-gram TF-IDF candidate channel
over an allowlisted identity-text projection. Character postings allow typo/spacing evidence to
admit candidates even without exact token overlap; dense ranking runs over the bounded token/char
union, and weighted RRF combines only ranks that exist.

Configuration is not chosen from v1. A separate 199-case development pack may select among exactly
21 predeclared character-floor/weight combinations through a safety-first deterministic rule. If no
configuration qualifies, v2 stays active and the feature stops. If one qualifies, its source and
artifact are committed before a new output-blind 105-case holdout v2 is written and reviewed by the
project owner.

## Why this direction

Simply running the current hashing vector over every document would be smaller but would lack an
interpretable eligibility floor and could admit collision/generic-text false positives. A neural
sentence-transformer is potentially stronger, but its model download, cache, license, checksum,
memory, offline packaging, and performance surface are disproportionate before a deterministic
spelling-oriented baseline is tested. Hard family quotas were rejected because they manufacture a
type advantage and could conceal valid merge-to-variant behavior.

Character TF-IDF with inverted postings is explainable, deterministic, compatible with the current
offline architecture, and more directly targets spelling/spacing identity variation. The accepted
cost is a new score/index/config artifact and a stricter test lifecycle. The system remains Dual
RAG: the canonical RAG alone decides identity, while the redesigned Human Knowledge RAG remains
debug/review evidence.

## Gates and 10x review

The development grid cannot produce v3 unless it has zero forbidden-family hits, zero unrelated
non-empty results, merge Recall@5 `1.0`, overall development Recall@5 at least `0.90`, and every
positive development style at least `0.85`. A deterministic objective/tie-break then selects one
winner. Final holdout v2 keeps the original v1 thresholds; no lowering is proposed.

The character path uses gram postings instead of a full identity scan and includes a clearly labeled
synthetic 3,000-document p95 smoke gate. That smoke is only an algorithmic warning for the later
scale target; it is not PostgreSQL, real-data, concurrent, or production evidence. T49 remains
blocked until the independently authored v2 holdout and complete QA both pass.

The most likely failure is a recall/safety conflict: low character thresholds can retrieve typos but
also turn generic text into suggestions; high thresholds can reproduce the v2 misses. The finite
grid and safety-first filter force that trade-off to be visible instead of expanding parameters
after results are seen.

## Confirmation gate

The project owner must confirm requirements, design, and task order before HRR-T1 creates the
development dataset. Later, a second owner confirmation is required after v3 is frozen and the new
v2 query/reference pack is shown; only then may labels and final retrieval be created.
