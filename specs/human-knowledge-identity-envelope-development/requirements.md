# Human Knowledge query-global identity envelope — Requirements

Date: 2026-09-21. Mode: Lite / Lean Industrial. Status: **HIE-T3 historical calibration FAIL; experiment stopped**.

## Goal

Develop a new public-only admission experiment that evaluates every retrieved candidate against one
query-global identity envelope. The experiment must prevent candidate-specific span selection or
compact matching from hiding model-number evidence while preserving legitimate identity shorthand
such as `88 Jeep Wagoneer` for `1988 Jeep Wagoneer`.

This is a new versioned experiment after identity-contradiction v1 produced a valid null winner. It
must not edit, overwrite, or retune v1 artifacts.

## Requirements

### HIE-R1 — Public-only development boundary

WHEN this feature reads development inputs, THE SYSTEM SHALL read only committed public corpus,
public development artifacts, and this feature's own public artifacts; it SHALL NOT read or name
private local queries, labels, candidates, ranks, results, or projection paths.

### HIE-R2 — Preserve v1 as immutable evidence

WHEN v2 development begins, THE SYSTEM SHALL treat the HIC v1 source, pack, protocol, raw rows,
selection, and their hashes as immutable upstream evidence. It SHALL NOT overwrite, relabel,
rescore in place, or add exceptions to v1.

### HIE-R3 — New family-disjoint public holdout

WHEN the v2 holdout is frozen, THE SYSTEM SHALL create exactly 32 new cases: sixteen
positive-preservation cases and sixteen absent-identity cases. Positive cases SHALL use sixteen
distinct public knowledge documents not used by any v4 or HIC-v1 positive, with four cases from
each of `abbreviation_numeric`, `contextual_noise`, `single_edit`, and `spacing_punctuation`.
Negative identities and normalized queries SHALL be absent from the corpus and SHALL not repeat any
v4 or HIC-v1 negative identity/query.

### HIE-R4 — Query-global identity envelope

WHEN a query is evaluated, THE SYSTEM SHALL construct one normalized identity envelope before any
candidate admission decision. The selected envelope, atom offsets, and included numeric/model atoms
SHALL be identical for every candidate retrieved for that query; a candidate SHALL NOT select a
shorter or different query span to improve its own compatibility.

### HIE-R5 — Numeric and alphanumeric conservation

WHEN an alphabetic model frame has an adjacent digit run in the query or candidate identity, THE
SYSTEM SHALL keep that digit run inside the comparison and SHALL NOT allow fuzzy or compact matching
to consume, omit, or move it outside the envelope. Different conserved digit runs in the same model
frame SHALL be explicit conflict evidence.

### HIE-R6 — Auditable shorthand equivalence

WHEN a two-digit leading identity token and a four-digit candidate token are compared, THE SYSTEM
MAY treat them as equivalent only under one predeclared structural rule that proves the final two
digits are equal and the four-digit value uses an allowed century prefix. The evidence SHALL record
the original tokens, normalized tokens, equivalence rule, and reason code. No release-year field or
case-specific vehicle rule may be consulted.

### HIE-R7 — Strict identity-field boundary

WHEN envelope or compatibility evidence is computed, THE SYSTEM SHALL use only normalized query
text and candidate casting/approved aliases. It SHALL NOT use series, color, edition, packaging,
release metadata, pricing, source provenance, private labels, knowledge IDs, case IDs, or
per-casting exception lists as decision evidence.

### HIE-R8 — Structured policy rather than another single scalar cutoff

WHEN rank-1 admission policies are declared, THE SYSTEM SHALL combine predeclared structural states
such as exact/alias compatibility, shorthand equivalence, conserved numeric conflict, unmatched
model atoms, manufacturer agreement, and envelope completeness. It SHALL NOT select a winner by
changing only one bilateral-residual threshold or by adding a case-specific exception. Ranks 2–5
SHALL preserve the frozen identity-token coverage `>= 0.75` rule and source order.

### HIE-R9 — Freeze-before-evaluation and exactly-once retrieval

WHEN the experiment runs, THE SYSTEM SHALL freeze the query-envelope rules, policy grid, holdout
selection rules, source hashes, exact gates, and winner ordering before collecting the 32 new
queries. It SHALL retrieve each new query exactly once at Top 5, persist label-blind raw rows before
scoring, and reuse those bytes for every policy. Existing 223-row, v4 22-row, and HIC-v1 24-row
public evidence SHALL be rescored without rerunning retrieval.

### HIE-R10 — Candidate-level explainability

WHEN a candidate is evaluated, THE SYSTEM SHALL emit the query-global envelope, candidate identity
form, ordered alignments, conserved and equivalent numeric atoms, unmatched discriminative atoms,
manufacturer relation, structural state, reason codes, and final admit/abstain decision. Every field
SHALL be deterministically recomputable without a network or external model call.

### HIE-R11 — Exact regression and holdout gates

WHEN a policy is scored, THE SYSTEM SHALL require all existing HIC-R8 gates, full preservation of
the HIC-v1 12 positive cases with zero output for its 12 negative cases, 16/16 new positive hits,
0/16 new absent-identity nonempty results, and zero retrieval, envelope, alignment, or decision
errors. A policy that improves negatives but loses any required positive SHALL be ineligible.

### HIE-R12 — Deterministic fail-closed outcome

WHEN all frozen policies have been scored, THE SYSTEM SHALL select a winner only from policies that
pass every exact gate, using the predeclared ordering. IF no policy is eligible, THEN THE SYSTEM
SHALL persist `winner: null`, identify every failed gate, and authorize no private evaluation or
runtime change.

### HIE-R13 — Immutable reproducibility

WHEN pack, protocol, raw, model/rule, or selection artifacts already exist, THE SYSTEM SHALL verify
their bytes and bound source hashes and return `unchanged`. IF any frozen input or computed field
differs, THEN THE SYSTEM SHALL fail closed without overwriting evidence or rerunning retrieval.

### HIE-R14 — Development-only release boundary

WHEN an eligible public policy exists, THE SYSTEM SHALL qualify it only for a newly versioned private
shadow-evaluation design. It SHALL NOT modify the API, Dual RAG runtime, PostgreSQL, canonical
identity, release promotion, variant UUID, color, wheel, tampo, edition, or packaging behavior.

## Out of scope

- Learning from HIC-v1 or private failures through per-case exceptions.
- Neural cross-encoders, external model calls, or new runtime dependencies.
- Variant-level physical-feature resolution.
- Runtime activation or execution of another private evaluation.
- Editing or deleting any v1 artifact.

## Feasibility evidence

The committed public data contains 144 unused correct rank-1 cases after excluding v4 and HIC-v1
source cases. Excluding every document used by either prior positive pack still leaves 93 cases from
24 documents: 22 abbreviation/numeric, 24 contextual-noise, 23 single-edit, and 24
spacing/punctuation cases. The required sixteen-document holdout is therefore feasible without
reusing a prior positive family.

## Acceptance checkpoint

The owner confirmed these requirements before design and implementation. HIE-T1–T3 completed, and
the historical gate failed with zero eligible non-reference policies. The new holdout, retrieval,
private evaluation, and every downstream integration remain blocked.
