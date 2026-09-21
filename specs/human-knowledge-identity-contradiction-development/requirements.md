# Human Knowledge candidate-specific identity contradiction — Requirements

Date: 2026-09-21. Mode: Lite / Lean Industrial. Status: **owner confirmed; implementation complete**.

## Goal

Develop a public-only admission experiment that can reject a retrieved candidate when the query
contains casting-identity evidence that contradicts that candidate. The experiment must improve on
the rejected v4 scalar confidence without using private evaluation failures as development labels.

## Requirements

### HIC-R1 — Public-only development boundary

WHEN this feature reads development inputs, THE SYSTEM SHALL read only committed public corpus,
public development packs, public raw retrieval rows, and this feature's own public artifacts; it
SHALL NOT read or name private local projection, query, label, candidate, rank, or result paths.

### HIC-R2 — New balanced pack frozen before retrieval

WHEN the contradiction pack is created, THE SYSTEM SHALL freeze exactly 24 cases before any new
retrieval: twelve positive-preservation cases and twelve absent-identity contradiction cases. The
positive cases SHALL exclude the ten positive cases used by anchor-confidence v4, span at least ten
distinct public knowledge documents, and already have a correct public source-rank-1 result. The
negative identities SHALL be absent from every committed casting and approved alias and SHALL not
repeat a v4 missing-identity case.

### HIC-R3 — Declared challenge coverage

WHEN the 12 negative cases are frozen, THE SYSTEM SHALL label each with one declared challenge type
from manufacturer agreement plus model substitution, numeric model conflict, compact or punctuated
model conflict, manufacturer conflict with descriptor overlap, and descriptor-overlap confusion;
the pack SHALL contain at least two cases from each type represented by the frozen protocol.

### HIC-R4 — Candidate-specific auditable evidence

WHEN a query-candidate pair is evaluated, THE SYSTEM SHALL emit normalized candidate identity,
selected query span, one-to-one token or compact-form alignments, unmatched identity-bearing query
tokens, unmatched candidate tokens, numeric conflict state, contradiction reason codes, and a final
admit or abstain decision. Every emitted value SHALL be deterministically recomputable from the
query plus the candidate's casting and approved aliases.

### HIC-R5 — Strict field and exception boundary

WHEN contradiction evidence is computed, THE SYSTEM SHALL use only casting and approved alias
fields already allowed by Human Knowledge identity retrieval. It SHALL NOT use series, color,
edition, packaging, release year, pricing text, source provenance, private labels, knowledge IDs,
case IDs, or per-casting exception lists as decision evidence.

### HIC-R6 — Frozen policy family before retrieval

WHEN the experiment protocol is frozen, THE SYSTEM SHALL declare the complete contradiction-policy
grid, token normalization, alignment modes, discriminative-token rules, numeric-conflict behavior,
secondary-candidate rule, source hashes, gates, and winner ordering before collecting any new raw
row. The existing v3 secondary rule SHALL remain identity-token coverage at least `0.75`, and source
order SHALL remain unchanged.

### HIC-R7 — Exactly-once collection and raw reuse

WHEN the frozen experiment runs, THE SYSTEM SHALL retrieve each of the 24 new queries exactly once
at Top 5, persist those raw candidates before reading expected labels for scoring, and reuse the same
raw rows for every policy. Existing 223-row public evidence and frozen v4 raw rows SHALL be rescored
without rerunning their retrieval.

### HIC-R8 — Exact regression and safety gates

WHEN a policy is evaluated, THE SYSTEM SHALL require all of the following for eligibility:

- 168/168 existing positive hits, 4/4 merge controls, zero existing governance violations, zero
  unrelated nonempty results, and 24/24 prior required hits;
- 10/10 v4 valid low-coverage anchor hits and 0/12 v4 missing-identity nonempty results;
- 12/12 new positive-preservation hits and 0/12 new absent-identity nonempty results;
- zero retrieval or contradiction-computation errors.

### HIC-R9 — Deterministic outcome and fail-closed selection

WHEN every frozen policy has been scored, THE SYSTEM SHALL select only an eligible policy using the
predeclared winner ordering. IF no policy passes every gate, THEN THE SYSTEM SHALL persist a null
winner, identify each failed gate, and authorize no private evaluation or runtime change.

### HIC-R10 — Immutable, reproducible artifacts

WHEN pack, protocol, raw result, or selection artifacts already exist, THE SYSTEM SHALL validate
their bytes and source hashes and return `unchanged`; IF any frozen input or computed field differs,
THEN THE SYSTEM SHALL fail closed without overwriting evidence or rerunning retrieval.

### HIC-R11 — Development-only release boundary

WHEN an eligible public policy exists, THE SYSTEM SHALL qualify it only for one newly versioned
private shadow-evaluation design. It SHALL NOT modify the API, Dual RAG runtime, PostgreSQL,
canonical identity, release promotion, variant UUID, color, wheel, tampo, edition, or packaging
behavior.

## Out of scope

- Learning from or adding exceptions for private failed cases.
- Neural rerankers, external model calls, or new runtime dependencies.
- Variant-level physical-feature resolution.
- Runtime activation or another private evaluation in this feature.

## Acceptance checkpoint

Requirements are accepted only after the owner confirms this document. Design and tasks must not
be treated as approved before that confirmation.
