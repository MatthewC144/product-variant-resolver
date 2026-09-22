# Human Knowledge identity-claim graph v3 — Requirements

Date: 2026-09-22. Mode: Lite / Lean Industrial. Status: **closed at historical FAIL; HICG-T1–T4/T8 complete; HICG-T5–T7 blocked**.

## Goal

Develop a new public-only admission experiment that represents a query as one candidate-independent
identity-claim graph before judging any retrieved candidate. The experiment must preserve legitimate
year shorthand, bounded OCR/edit variants, abbreviations, compact spellings, and seller context while
rejecting explicit model-number contradictions at every source rank.

This is a new versioned experiment after identity-envelope v2 produced a valid null winner. It must
not edit, overwrite, reinterpret, or retune any HIC-v1 or HIE-v2 source or artifact.

## Requirements

### HICG-R1 — Public-only development boundary

WHEN v3 reads development inputs, THE SYSTEM SHALL read only committed public corpus, committed
public development evidence, and v3's own public artifacts. It SHALL NOT read or name private local
queries, labels, candidates, ranks, results, projection documents, or owner-only release rows.

### HICG-R2 — Preserve prior experiments as immutable evidence

WHEN v3 development begins, THE SYSTEM SHALL verify and record the hashes of the frozen HIC-v1
source and the frozen HIE-v2 source, calibration JSON, manifest, and Markdown report. It SHALL NOT
overwrite, relabel, rescore in place, or add an exception to either experiment.

### HICG-R3 — One candidate-independent identity-claim graph

WHEN a query is evaluated, THE SYSTEM SHALL construct exactly one normalized identity-claim graph
before evaluating any candidate. The graph SHALL identify ordered identity anchors, numeric or
alphanumeric frames, context atoms, unresolved discriminative atoms, atom offsets, and relations.
The same graph and checksum SHALL be supplied to every candidate for that query; a candidate SHALL
NOT select, delete, or reclassify query atoms to improve its own compatibility.

### HICG-R4 — Auditable context boundary

WHEN query atoms are classified as context rather than identity, THE SYSTEM SHALL use only a
predeclared public lexicon and candidate-independent structural rules frozen before scoring. Seller
or packaging words such as `listing`, `sale`, and `unboxed` MAY be context; vehicle maker, model,
year, and unresolved discriminative atoms SHALL NOT be discarded merely because a candidate lacks
them. Every context decision SHALL emit a deterministic reason code.

### HICG-R5 — Frame-local numeric conservation

WHEN the query or candidate contains a numeric or alphanumeric model/year expression, THE SYSTEM
SHALL compare it inside its local identity frame rather than comparing a global tuple of all digits.
The system SHALL preserve the original token, normalized token, frame owner, digit run, and relation.
It SHALL NOT allow compact or fuzzy alignment to consume, omit, or move the digits outside that frame.

### HICG-R6 — Bounded year and OCR equivalence

WHEN two numeric frames differ, THE SYSTEM MAY declare equivalence only through a frozen structural
rule: a leading two-digit year may equal a leading `19xx` or `20xx` year when their final two digits
match, and an OCR substitution such as `o`/`0` may apply only inside the same alphanumeric frame with
the non-substituted frame structure conserved. Each use SHALL record the rule and both source forms.
Release metadata, case IDs, labels, and vehicle-specific exception lists SHALL NOT be consulted.

### HICG-R7 — Bounded edit and abbreviation equivalence

WHEN an anchor differs through spacing, punctuation, abbreviation, or a small edit, THE SYSTEM MAY
relate the forms only through a frozen, corpus-derived inventory built from committed casting names
and approved aliases, or through a predeclared bounded structural edit rule. The inventory SHALL be
candidate-independent and auditable. It SHALL NOT contain evaluation-case exceptions or mappings
learned from expected labels.

### HICG-R8 — Universal hard-conflict veto before rank policy

WHEN any rank 1–5 candidate has an explicit conserved numeric/alphanumeric model conflict with the
query claim graph, THE SYSTEM SHALL abstain from that candidate before applying rank-specific
coverage or positive-admission rules. The existing rank 2–5 identity-token coverage `>= 0.75` rule
MAY run only after this veto. In particular, a secondary candidate SHALL NOT be admitted solely by
coverage when the query claims `R32` or `R33` and the candidate claims `BNR34`.

### HICG-R9 — Structured positive admission

WHEN no universal hard conflict exists, THE SYSTEM SHALL decide admission from predeclared
categorical evidence including anchor relation, frame-local numeric relation, graph completeness,
context separation, unresolved discriminative atoms, form completion, and source rank. It SHALL NOT
select a winner by tuning one scalar cutoff or by adding a casting-, query-, or case-specific rule.
Source candidate order SHALL remain unchanged.

### HICG-R10 — Strict identity-field boundary

WHEN claim-graph or compatibility evidence is computed, THE SYSTEM SHALL use only normalized query
text and candidate casting/approved aliases. It SHALL NOT use series, color, wheel, tampo, edition,
packaging, release year metadata, price, source provenance, knowledge IDs, case IDs, or private
labels as decision evidence.

### HICG-R11 — Historical calibration before any new retrieval

WHEN v3 policies are calibrated, THE SYSTEM SHALL reuse the frozen 223-row, v4 22-row, and HIC-v1
24-row public evidence without rerunning retrieval. Eligibility SHALL require all of the following:

- 168/168 existing positive hits, 4/4 merge controls, zero existing governance violations, zero
  unrelated nonempty results, and 24/24 prior required hits;
- 10/10 v4 valid low-coverage anchor hits and 0/12 v4 missing-identity nonempty results;
- 12/12 HIC-v1 positive-preservation hits and 0/12 HIC-v1 absent-identity nonempty results;
- both known secondary numeric-conflict failures (`R32` and `R33` versus `BNR34`) abstained;
- zero retrieval, graph, alignment, or decision errors.

### HICG-R12 — Historical branch gate and fail-closed null result

WHEN historical calibration finishes, THE SYSTEM SHALL select a survivor only from policies that
pass every HICG-R11 gate, using a predeclared ordering. IF no non-reference policy survives, THEN THE
SYSTEM SHALL persist `winner: null`, identify every failed gate, keep new retrieval calls at zero,
and stop before creating a v3 holdout protocol, pack, raw rows, or selection report.

### HICG-R13 — New family-disjoint holdout only after historical success

WHEN and only when a non-reference policy passes HICG-R11, THE SYSTEM SHALL freeze source, policies,
gates, ordering, protocol schema, and holdout-selection rules before materializing exactly 32 new
public cases. The holdout SHALL contain sixteen positive-preservation cases from sixteen public
knowledge documents unused by the v4 and HIC-v1 positive packs, balanced across leading-year/context,
frame-local OCR/numeric, bounded edit/abbreviation, and compact spacing/punctuation challenges. It
SHALL also contain sixteen new corpus-absent hard negatives balanced across numeric model conflict,
same-maker model substitution, compact-digit conflict, and context-overlap challenges.

### HICG-R14 — Exactly-once label-blind collection and exact holdout gates

WHEN the frozen 32-case holdout is run, THE SYSTEM SHALL retrieve every query exactly once at Top 5,
persist label-blind raw rows before scoring, and reuse those exact bytes for every policy. Eligibility
SHALL require 16/16 positive hits, 0/16 absent-identity nonempty results, zero retrieval/graph/decision
errors, and all HICG-R11 historical gates. Seeing holdout labels or outcomes SHALL NOT authorize a
source or policy change.

### HICG-R15 — Candidate-level explainability and reproducibility

WHEN a candidate is evaluated, THE SYSTEM SHALL emit the immutable query graph and checksum,
candidate identity form, ordered alignments, context decisions, numeric/alphanumeric frames,
equivalence rules, unresolved and unmatched identity atoms, hard-conflict result, rank rule, reason
codes, and final admit/abstain decision. All fields SHALL be deterministically recomputable offline.
Existing v3 artifacts SHALL be byte- and hash-validated and returned as `unchanged`; mismatches SHALL
fail closed without overwrite or retrieval.

### HICG-R16 — Development-only release boundary

WHEN an eligible public policy exists, THE SYSTEM SHALL qualify it only for a separately specified,
newly versioned private shadow evaluation. It SHALL NOT modify the API, Dual RAG runtime,
PostgreSQL data, canonical identity, release promotion, variant UUID, color, wheel, tampo, edition,
or packaging behavior.

## Out of scope

- Reading the five-family private projection or its 20-case shadow-evaluation results.
- Learning case-specific mappings from HIC-v1, HIE-v2, private failures, or expected labels.
- Neural cross-encoders, external model calls, new runtime dependencies, or online training.
- Variant-level physical-feature resolution or color inference.
- Runtime activation, canonical promotion, database writes, or another private evaluation.
- Editing or deleting prior experiment source or artifacts.

## Public feasibility and failure evidence

HIE-v2 historical calibration executed zero new retrieval calls and produced no eligible policy.
Its strongest safety-oriented policy, `envelope-bilateral`, reduced v4 and HIC-v1 absent-identity
nonempty results to 1/12 each, but also reduced existing positive hits to 146/168, v4 positives to
9/10, and HIC-v1 positives to 10/12. Public row-level evidence shows recurring loss modes in leading
year/context queries, local OCR or multi-number frames, bounded abbreviation/edit cases, and compact
spellings.

The final two admitted hard negatives are both secondary candidates: `R32` and `R33` queries admit
a `BNR34` identity through `secondary_coverage_at_least_075`, bypassing the rank-1 structural
conflict logic. This supports a universal conflict veto plus a richer candidate-independent claim
graph; it does not prove that v3 will have an eligible winner.

## Acceptance checkpoint

The owner confirmed requirements, design, and tasks sequentially before implementation. HICG-T1–T4
and the historical-FAIL closure branch of HICG-T8 are complete. The formal 223/22/24 public
historical calibration returned `winner: null`: no non-reference policy passed every HICG-R11 gate.
Exactly three null-calibration files were persisted, retrieval remained zero, and
protocol/pack/raw/selection artifacts remain absent. HICG-T5–T7 remain blocked by HICG-R12. QA maps
all HICG-R1–R16 outcomes and does not authorize private evaluation or runtime integration.
