# Human Knowledge identity-certificate set v4 — Requirements

Date: 2026-09-24. Mode: Lite / Lean Industrial. Status: **CLOSED — historical FAIL; HICS-T6–T8 blocked; Pointwise/Listwise spec next**.

## Goal

Develop a new public-only admission experiment that resolves a query to a candidate-independent set
of public casting/family identity authorities through corpus-wide minimal identity certificates. A
certificate is the smallest auditable combination of primary-casting atoms and local numeric frames
that uniquely distinguishes one casting/family identity authority from every other authority in the
committed corpus. Approved aliases may provide bounded match surfaces but may not introduce new
certificate claims.

The experiment must preserve legitimate partial names, compact spellings, bounded typos, year
shorthand, and listing context without admitting a different casting merely because it shares a
manufacturer or generic model word. It follows the valid null result from HICG-v3 and must not edit,
overwrite, relabel, or retune any HIC-v1, HIE-v2, or HICG-v3 source or evidence.

## Requirements

### HICS-R1 — Public-only development boundary

WHEN v4 reads development inputs, THE SYSTEM SHALL read only committed public corpus, committed
public development evidence, and v4's own public artifacts. It SHALL NOT read or name private local
queries, labels, candidates, ranks, results, owner release rows, or projection documents.

### HICS-R2 — Preserve prior experiments as immutable evidence

WHEN v4 development begins, THE SYSTEM SHALL verify and record the hashes of the frozen HIC-v1,
HIE-v2, and HICG-v3 sources plus their final selection or calibration evidence. It SHALL NOT
overwrite, rescore in place, rename, or add an exception to any prior experiment.

### HICS-R3 — Corpus-wide minimal identity certificates

WHEN the public grammar is built, THE SYSTEM SHALL group provisional-variant documents by their
casting ID and review-family documents by their review-family ID, then derive one or more minimal
identity certificates from each group's primary casting. Each certificate SHALL contain an ordered,
nonempty combination of normalized identity atoms and local numeric/alphanumeric frames that
distinguishes exactly one authority key from every other public authority key. Approved aliases MAY
map query text onto existing primary-casting claims but SHALL NOT create new claims. Redundant
supersets SHALL be removed deterministically. A group with no unique certificate SHALL remain
explicitly unresolved and ineligible rather than using series, color, or variant fields.

### HICS-R4 — Certificate provenance and stability

WHEN a certificate is emitted, THE SYSTEM SHALL record its authority key, member knowledge IDs,
primary casting, atom/frame positions, competing authorities eliminated by each claim, minimality
proof, and deterministic checksum. Documents within the same casting authority MAY share a
certificate; evidence from another authority SHALL NOT be merged into it. A certificate SHALL NOT
claim that multiple provisional variants within one authority are distinguishable.

### HICS-R5 — Candidate-independent query support set

WHEN a query is evaluated, THE SYSTEM SHALL normalize and align it against the complete frozen
certificate inventory before evaluating retrieved candidates. It SHALL produce a support set of
authority keys whose complete certificate is satisfied by the query. Retrieved candidate documents,
source ranks, scores, or metadata SHALL NOT create, remove, or reorder support-set members.

### HICS-R6 — Complete certificate, not shared-token admission

WHEN a query shares only a manufacturer, generic model word, or incomplete certificate with a
public authority, THE SYSTEM SHALL NOT add that authority to the support set. Queries such as `Honda
Accord`, `BMW M4`, or `Bugatti Divo` SHALL NOT resolve to a different corpus identity solely through
shared `Honda`, `BMW`, `Bugatti`, `model`, `performance`, or other non-unique atoms.

### HICS-R7 — Legitimate partial-name preservation

WHEN a query satisfies a complete certificate that uniquely identifies one authority key, THE SYSTEM
MAY tolerate candidate-name atoms not present in the query. A legitimate unique shorthand such as a
year/model/manufacturer combination SHALL NOT fail merely because the candidate's full casting name
contains additional words. The exact certificate and omitted candidate atoms SHALL remain visible.

### HICS-R8 — Frozen bounded equivalence

WHEN matching query claims to a certificate, THE SYSTEM MAY use only predeclared structural
equivalences frozen before historical scoring: punctuation/spacing normalization, compact
segmentation, unique prefix abbreviation, alphabetic Damerau-Levenshtein edit distance one,
leading two-/four-digit year equivalence, same-frame `o`/`0`, repeated-digit restoration, and
leading-year uncertainty `x`. Each use SHALL preserve both source forms and a reason code. Numeric
substitution or movement between frames SHALL remain forbidden.

### HICS-R9 — Ambiguity and unresolved identity claims fail closed

WHEN no complete certificate is satisfied, or WHEN certificates from more than one authority key
remain supported, THE SYSTEM SHALL return no resolved identity and SHALL admit no candidate. A
non-context query atom that contradicts a certificate frame or satisfies a competing identity claim
SHALL remove that identity from the support set; it SHALL NOT be silently discarded to obtain a
singleton.

### HICS-R10 — Auditable context boundary

WHEN listing, packaging, scale, or uncertainty language is treated as context, THE SYSTEM SHALL use
only a frozen public lexicon and candidate-independent structural rules. Identity participation has
precedence over context membership. Every ignored wrapper SHALL emit a reason code, and vehicle
manufacturer, model, year, or unresolved discriminative terms SHALL NOT become context merely
because the corpus lacks the requested identity.

### HICS-R11 — Candidate membership and universal conflict veto

WHEN the support set contains exactly one authority key, THE SYSTEM SHALL admit only retrieved
candidates mapped to that key. Multiple provisional documents under the same casting key MAY remain
visible in original source order but SHALL NOT be represented as variant-level resolution. A
primary-casting conserved numeric/alphanumeric conflict SHALL veto admission at ranks 1–5 even if an
alias omits the frame. Candidate order and source rank SHALL remain unchanged.

### HICS-R12 — Strict identity-field boundary

WHEN certificates, query support, or candidate membership are computed, THE SYSTEM SHALL use only
normalized query text and committed candidate casting/approved aliases. It SHALL NOT use series,
color, wheel, tampo, edition, packaging, release-year metadata, price, source provenance, case IDs,
expected labels, knowledge UUID ordering, or private outcomes as decision evidence.

### HICS-R13 — Historical calibration before new retrieval

WHEN v4 configurations are calibrated, THE SYSTEM SHALL reuse the frozen 223-row, v4 22-row, and
HIC-v1 24-row public evidence without rerunning retrieval. Eligibility SHALL require all prior exact
positive, merge, governance, unrelated-output, required-target, absent-identity, `R32/R33` versus
`BNR34`, and zero-error gates already formalized by HICG-R11. Certificate construction, query
support, alignment, decision, and retrieval errors SHALL each equal zero.

### HICS-R14 — Historical branch gate and null result

WHEN historical calibration finishes, THE SYSTEM SHALL select only a non-reference configuration
that passes every HICS-R13 gate under a predeclared ordering. IF none survives, THEN THE SYSTEM SHALL
persist `winner: null`, identify every failed gate, keep new retrieval at zero, and stop before
creating a protocol, holdout pack, raw rows, private evaluation, or runtime change.

### HICS-R15 — Conditional family-disjoint holdout and reproducibility

WHEN and only when historical calibration succeeds, THE SYSTEM SHALL freeze source, certificate
inventory, equivalence/context rules, configurations, gates, winner order, and a new family-disjoint
public holdout protocol before retrieval. Collection SHALL be exactly once and label-blind; all
artifacts SHALL be byte/hash validated. Existing valid bytes return `unchanged`; mismatch, partial
state, schema drift, or source drift SHALL fail closed without overwrite or additional retrieval.

### HICS-R16 — Explainability and development-only release boundary

WHEN a query or candidate decision is inspected, THE SYSTEM SHALL expose the frozen certificate
inventory hash, query support authority keys, member knowledge IDs, complete/missing claims,
equivalence uses, ambiguity competitors, context decisions, candidate authority membership, primary
conflict result, source rank, reason codes, and final decision. Even an eligible public winner SHALL
qualify only for a separately specified private shadow evaluation. It SHALL NOT modify the API,
Dual RAG runtime, PostgreSQL data, canonical identity, release promotion, variant UUID, color,
wheel, tampo, edition, or packaging behavior.

## Out of scope

- Reading the private five-family projection or its 20-case shadow results.
- Learning exception mappings from expected labels, HIC/HIE/HICG failures, or owner release rows.
- Retuning HICG-v3 in place or overwriting its null calibration.
- Neural cross-encoders, external model calls, online training, or a new runtime dependency.
- Variant-level color, wheel, tampo, edition, packaging, or release promotion.
- Runtime activation, canonical writes, database writes, or another private evaluation.

## Public failure evidence motivating v4

HICG-v3 exposes two opposite errors. Its loose policies admit absent identities after matching only
shared manufacturer or generic atoms: public examples include `Honda Accord` resolving toward a
Honda Civic identity, `BMW M4` toward BMW M1, and `Bugatti Divo` toward Bugatti Veyron. They also
miss both secondary `R32/R33` versus `BNR34` veto gates.

Its strict policies eliminate every measured absent-identity output but reject valid shorthands and
noisy identities whenever the candidate's full name or an unresolved wrapper remains. Public
examples include compact `fishdchipd`, `x34landspeeder`, `kowloondhypervan`, bounded typo `kick kat`,
and partial `55 Chevy`. The certificate-set approach addresses this specific boundary: admission
requires a complete corpus-wide uniqueness proof, not complete equality with the candidate name and
not a shared-token score.

## Acceptance checkpoint

The owner confirmed the bounded sequence on 2026-09-23: complete v4 through its branch-aware public
closure, then return to the original pointwise-versus-listwise reranking milestone, with no automatic
v5 iteration. V4 resolves 139 casting/family authority keys represented by 142 documents; it does
not distinguish provisional variants sharing one casting. Implementation integrity passed, but the
formal 223/22/24 calibration returned `winner: null`: the three certificate profiles were safe on
measured negatives yet failed required positive-preservation gates. HICS-T6–T8 are therefore
blocked. The branch closes with three public calibration files, zero new retrieval, and no protocol,
holdout, private evaluation, database, API, or runtime authorization. The next specification must
compare No Reranker/RRF, Neural Pointwise, and Listwise rather than create v5.
