# Human Knowledge identity-claim graph v3 — Design

Date: 2026-09-22. Mode: Lite / Lean Industrial. Status: **closed at historical FAIL; HICG-T1–T4/T8 complete; HICG-T5–T7 blocked**.

## Overview

HIE-v2 proved that one query-global envelope is safer than a candidate-selected span, but a single
linear boundary still mixes several roles: seller context, identity words, leading year shorthand,
standalone model numbers, and compact alphanumeric frames. Its strongest safety policy reduced both
historical negative sets to one admitted case, yet it lost 22 existing positives, one v4 positive,
and two HIC-v1 positives. The last two negatives also bypassed structural checks because they were
secondary candidates admitted directly by coverage.

V3 replaces the linear envelope with one immutable identity-claim graph per query. The graph is
built from the whole committed public identity corpus before any Top-5 candidate is examined. Every
candidate then answers the same claims. A universal numeric/alphanumeric conflict veto runs for
ranks 1–5 before any rank-specific rule, while bounded context, year, OCR, abbreviation, edit, and
compact-form rules protect legitimate positives.

This is an offline public-development experiment. It does not change retrieval, the API, Dual RAG,
PostgreSQL, canonical identities, or release-variant behavior.

## Architecture and freeze order

```text
committed public corpus + frozen 223/v4-22/HIC-v1-24 evidence
                              |
                              v
       build public identity grammar and one graph per query
                              |
                              v
       compare every candidate through all-rank conflict preflight
                              |
                              v
       historical calibration (no retrieval; exact gates)
                              |
                 no survivor +-----------+ survivor
                      |                                 |
                      v                                 v
          persist null calibration       freeze source + protocol rules
          and stop at 0 retrieval                     |
                                                        v
                                      materialize family-disjoint 16+16 pack
                                                        |
                                                        v
                                      collect 32 Top-5 rows exactly once
                                                        |
                                                        v
                                      score frozen policies or return null
```

Implementation will be isolated in
`src/product_variant_resolver/human_knowledge_identity_claim_graph_development.py`. Runtime modules
must not import it. HIC-v1 and HIE-v2 source/artifacts remain read-only upstream evidence.

### Immutable upstream bindings

Historical calibration and every later manifest must verify these exact SHA-256 values before use:

| Upstream evidence | SHA-256 |
|---|---|
| HIC-v1 source | `167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f` |
| HIE-v2 source | `c91d8e253f1cd19cf59b626e794673defe2e28aea6c993cbce350d1698e83a5e` |
| HIE-v2 calibration JSON | `fbdc5171f3b1bfbe3f07b207acb56bd9608e2a3136bdff1acb9175e99f1557ce` |
| HIE-v2 calibration manifest | `03eee815b2cb4110e158f2ff02bf51d8b582282c1f050358c3be117ee238eeb5` |
| HIE-v2 calibration Markdown | `7e0fbd7e1f92cf0d043949e0c0fdee69bd4d53f0a9f40fe1a41d466f6b5039be` |

A mismatch stops V3 before graph construction and writes nothing.

## Public identity grammar

The constructor reads only each committed public document's casting and approved aliases. It
deduplicates normalized forms and builds these candidate-independent indexes:

- ordered public identity forms and their atom positions;
- exact and compact identity atoms;
- public atom document frequency for deterministic tie-breaking;
- eligible prefix-abbreviation expansions;
- eligible one-edit alphabetic expansions;
- numeric/alphanumeric frame shapes.

Knowledge IDs may validate uniqueness and provenance but cannot score or break an admission tie.
Final lexical ties use normalized form text, atom positions, and relation names.

### Frozen context vocabulary

V3 tokenizes the full normalized query before dropping anything. The existing public
`IdentityCorePolicy.NOISE` set becomes the base context vocabulary. A v3-only extension adds the
public development wrappers `listing`, `sale`, `unboxed`, `warehouse`, `preowned`, `quarter`,
`mile`, `street`, `racers`, `matchbox`, `lineage`, `unclear`, and `without`.

Vocabulary membership alone does not delete an atom. If a token is required by the winning
corpus-wide identity hypothesis—for example `model` in `Tesla Model S Plaid`—identity participation
wins. Otherwise a vocabulary atom becomes context with `public_context_token`. A non-vocabulary
atom that cannot be explained remains an unresolved discriminative claim; it is never silently
dropped because a candidate lacks it.

The exact vocabulary and precedence rule are serialized into the protocol. Adding a token after
historical or holdout results are visible requires a new experiment version.

## Query-graph construction

### 1. Normalize and atomize once

Normalize the full query with the existing Unicode/text normalization, but retain normalized-source
offsets and original source tokens. Split each token into ordered alphabetic and digit runs without
first applying the old noise deletion. Leading punctuation such as the apostrophe in `'87` remains
in provenance but does not prevent `87` from being typed as a numeric atom.

### 2. Segment compact tokens without changing digits

A deterministic segmenter may split one source token into public identity atoms and context atoms.
It searches the complete public grammar, not the retrieved candidates, and orders solutions by:

1. more exact identity atoms;
2. more conserved digit runs;
3. more total identity atoms;
4. fewer equivalence operations;
5. fewer segments;
6. lexical segment sequence.

Thus `2020ram1500rebel` can become `2020 | ram | 1500 | rebel`, and `smallbloc` can become context
`small` plus identity `bloc`. Segmentation cannot alter, reorder, merge, or discard a digit run.

### 3. Generate bounded public-form relations

The graph builder may use these frozen relations while aligning the query against every public
identity form:

- `exact` — normalized atoms are equal;
- `compact_exact` — the same atoms are recovered by deterministic compact segmentation;
- `unique_prefix_abbreviation` — an alphabetic query prefix has at least two characters, expands to
  an alphabetic public atom of at least five characters, at least one other identity atom aligns
  exactly/compactly, and the expansion is unique under that aligned remainder;
- `unique_alpha_edit_1` — alphabetic atoms of at least four characters have Damerau-Levenshtein
  distance exactly one, at least one other identity atom aligns exactly/compactly, and the expansion
  is unique under that aligned remainder.

The edit relation never applies to digit runs. These constraints support general forms such as
`de`/`deora`, `su`/`super`, `suer`/`super`, `moran`/`morgan`, and `cusom`/`custom` without storing a
case-specific mapping.

### 4. Select one corpus-wide identity hypothesis

Every public form competes under one lexicographic key: exact atoms, conserved numeric-frame slots,
total aligned identity atoms, public-IDF weight, fewer abbreviation/edit relations, later identity
start after leading context, longer explained form, then normalized lexical form. Numeric values are
recorded but not erased merely because the closest public form has a different value.

The winning hypothesis identifies query anchors and model slots. Because it searches the complete
public grammar before reading the row's candidates, every candidate receives the same result. If no
form has a bounded relation, the graph is `unanchored` and all non-context atoms remain unresolved.

### 5. Build atoms, frames, and edges

The graph contains ordered atoms with exactly one role:

```text
identity_anchor | identity_model | numeric_frame | context | unresolved_discriminative
```

It also contains these local frames:

- `leading_year` — a two- or four-digit atom immediately before the first identity atom after
  ignoring context;
- `standalone_model` — a digit atom occupying a slot between or after aligned identity atoms;
- `alphanumeric_model` — alphabetic and digit runs originating from one source token;
- `compact_model` — the same logical slots recovered from one compact source token.

Edges preserve `ordered_before`, `belongs_to_frame`, `modifies_anchor`, and `same_identity_slot`
relations. A frame owner is its kind plus adjacent aligned identity anchors and ordinal slot, rather
than a global tuple of every digit in the query. This separates the year `20` from model `1500` in
`20 Ram 1500 Rebel`.

The serialized graph includes the normalized query, atom provenance and offsets, chosen public-form
hypothesis, contexts, unresolved claims, frames, edges, rule versions, and a canonical JSON SHA-256
checksum.

## Numeric and alphanumeric equivalence

Comparable frames are evaluated locally. The following are the only non-exact numeric equivalences:

1. `leading_year_suffix` — two leading digits equal the final two digits of a leading `19xx` or
   `20xx` frame owned by the same identity anchor;
2. `ocr_o_zero` — `o` may become `0` only inside the same mixed alphanumeric frame when all other
   alphabetic and digit positions are conserved;
3. `ocr_repeated_digit_restore` — one adjacent repeated digit may be inserted or deleted inside the
   same local frame while the alphabetic skeleton remains equal, such as `50e`/`500e`;
4. `leading_year_uncertainty_x` — a token shaped as two/four digits followed by terminal `x`, placed
   immediately before the first identity anchor, contributes its digit prefix to the year frame and
   records `x` as a non-identity uncertainty marker.

No rule permits substitution between unequal digits, nonlocal digit movement, or equivalence across
different frame owners. `R33` versus `R34` and terminal `R33` versus `BNR34` therefore conflict even
when their alphabetic skeletons differ: after the shared surrounding identity anchors align, both
occupy the same terminal model slot and claim unequal digits.

## Candidate comparison and hard-conflict preflight

For each candidate document, V3 parses the primary casting and every approved alias. An alias may
provide a better positive alignment, but it cannot erase a contradictory numeric/alphanumeric claim
present in the primary casting. The preflight therefore compares query frames with the primary
casting first, then records alias evidence separately.

A universal hard conflict exists when comparable query and primary-casting frames both contain
digit claims and no frozen equivalence relates them. This preflight runs before checking source rank,
identity-token coverage, form completion, or policy configuration. Every non-reference policy must
abstain from a hard-conflict candidate at ranks 1–5.

After preflight, the best approved form is selected using a lexicographic evidence key. Candidate
evidence has these categorical states:

```text
graph_status             anchored | unanchored
anchor_relation          exact | alias_equivalent | bounded_equivalent | different | unavailable
numeric_relation         none | equal | year_suffix | ocr_equivalent | conflict | query_only | candidate_only
context_relation         separated | none
query_claim_residual     none | present
candidate_claim_residual none | present
form_completion          complete | partial
hard_conflict            pass | fail
source_rank              1 | secondary
```

Context atoms never count as residuals. Numeric frames, unresolved discriminative atoms, and
unmatched public identity atoms do. Every relation and selected form emits ordered reason codes.

## Frozen policy family

`reference-anchor` reproduces the current rank-1/secondary behavior for comparison and cannot be a
survivor. Every non-reference configuration first applies the all-rank hard-conflict veto, preserves
source order, and applies secondary coverage `>= 0.75` only after structural rules pass.

| Configuration | Ordered structural admission rule for every rank |
|---|---|
| `claim-conflict-veto` | Reject hard conflict; otherwise rank 1 passes and secondary candidates proceed to the 0.75 gate |
| `claim-bilateral` | Reject hard conflict, different anchor, or residual identity claims on both sides; otherwise proceed by rank |
| `claim-query-conservation` | Apply bilateral rules, then reject a query-only numeric/alphanumeric frame or unresolved query claim; otherwise proceed by rank |
| `claim-decision-list` | Admit complete exact/frozen-equivalent forms; otherwise reject hard conflict or different anchor; admit a unique bounded abbreviation/edit only with no residual identity claims; otherwise abstain |

“Proceed by rank” means rank 1 admits and ranks 2–5 must additionally satisfy the frozen 0.75
coverage gate. No configuration changes candidate order or promotes a lower candidate.

## Historical calibration and winner ordering

Before protocol creation, every policy rescans only the immutable 223-row, v4 22-row, and HIC-v1
24-row public evidence. There are no retrieval calls. A non-reference policy survives only when it
passes every HICG-R11 gate, including exact positive preservation, zero historical negative output,
both secondary `R32/R33` versus `BNR34` rejections, and zero computation errors.

If no policy survives, V3 writes only deterministic historical-calibration JSON, manifest, and
Markdown evidence with `winner: null`; protocol, pack, raw, and selection artifacts remain absent.
If one or more policies survive, all survivors are frozen before the new holdout is materialized.

Among policies that later pass both historical and new holdout gates, winner ordering is:

1. fewer admitted candidates across all negative cases;
2. fewer abstained source candidates across all positive/regression cases;
3. fewer non-exact equivalence operations;
4. explicit least-restrictive order: `claim-conflict-veto`, `claim-bilateral`,
   `claim-query-conservation`, `claim-decision-list`.

A null winner is valid and authorizes no private or runtime stage.

## Holdout construction after historical success

Only after a historical survivor and source/protocol freeze, the pack builder selects sixteen
positive cases from sixteen documents unused by v4 or HIC-v1 positives. It deterministically selects
four cases from each required challenge family using a protocol-bound SHA-256 key.

Sixteen new corpus-absent negatives are declared after source freeze, four each for numeric model
conflict, same-maker model substitution, compact-digit conflict, and context overlap. Validators
prove identity/query absence, non-reuse, family disjointness, balanced counts, and exact source
hashes before collection.

The 32 queries are retrieved once at Top 5. Raw rows are saved before expected labels are joined and
are reused byte-for-byte by every survivor. Retrieval errors are retained, never retried, and make
all policies ineligible.

## Interfaces and artifact lifecycle

The installed command will be `pvr-develop-human-knowledge-identity-claim-graph`:

```text
--freeze-protocol   calibrate historical rows; freeze source/rules only when a survivor exists
--freeze-pack       create/validate the family-disjoint 16+16 pack; no retrieval
--collect           make exactly 32 Top-5 calls and persist label-blind raw rows once
--score             join frozen labels and write deterministic selection artifacts once
--check             recompute and validate existing artifacts; no retrieval and no writes
```

Invalid phase order fails closed. From successful protocol freeze onward, the source module and
serialized grammar/policy definitions cannot change.

```text
specs/human-knowledge-identity-claim-graph-development/
  requirements.md
  design.md
  tasks.md
  holdout-negative-declarations.json        # only after successful protocol/source freeze
data/evaluation/human-knowledge-identity-claim-graph-development-v3/
  protocol/protocol.json
  protocol/protocol-manifest.json
  pack/development-pack.json
  pack/development-pack-manifest.json
  raw/raw.json
  raw/raw-manifest.json
reports/human-knowledge-identity-claim-graph-development-v3/
  historical-calibration.json
  historical-calibration-manifest.json
  historical-calibration.md
  selection.json
  selection.md
```

Raw rows contain queries, source-ranked candidates, retrieval work, and errors but no expected
labels, policy decisions, or winner fields. Every manifest binds exact source, public corpus, and
upstream evidence SHA-256 values. Existing artifacts are validated, never overwritten.

## Error handling

- Missing, malformed, reordered, duplicated, stale, partially written, or hash-mismatched evidence
  fails closed.
- Different graph checksums across candidates for one query, candidate-dependent role changes,
  deleted digit runs, invalid compact segmentation, ambiguous abbreviation/edit expansion, unknown
  states, or primary-casting conflict hidden by an alias are computation errors.
- Historical denominator drift or any failed exact gate stops before protocol/pack/retrieval.
- Pack family reuse, corpus-present negatives, wrong style counts, labels in raw rows, a call count
  other than 32, or changed source after freeze invalidates the experiment.
- Retrieval errors are persisted and never retried or removed.
- A defect discovered after source freeze preserves all evidence and requires a new version.

## Security and privacy notes

All inputs are committed public data. The module requires no private paths, browser, network access
during historical calibration, credentials, dynamic code execution, external model, or new runtime
dependency. The optional holdout collection uses only the project's existing public retrieval
interface after freeze. Existing query/token/work bounds remain enforced.

## Testing strategy

- Unit: full-query offsets, context precedence, compact segmentation, unique prefix/edit relations,
  graph determinism, graph checksum reuse, local frame ownership, four numeric equivalences, and
  alias non-bypass of primary conflicts.
- Regression positives: apostrophe years; `1988`/`88`; `94x`/`94`; `5o0`/`500`;
  `50e`/`500e`; `20 Ram 1500`/`2020 Ram 1500`; compact `2020ram1500rebel`;
  `de`/`deora`; `su`/`super`; `suer`/`super`; `moran`/`morgan`; `cusom`/`custom`;
  compact context plus identity; leading/trailing seller context.
- Adversarial negatives: rank-1 and secondary `R32`/`R33` versus `BNR34`, unequal digits in the
  same slot, alias missing the conflicting primary frame, context-only overlap, ambiguous prefix,
  digit substitution, and unanchored input.
- Contract: exact 223/22/24 historical denominators and gates, zero historical retrieval, conditional
  protocol creation, 16+16 family-disjoint pack, exactly-once collection, label-blind raw schema,
  immutable hashes, and phase order.
- Artifact: deterministic winner/null, failure-gate details, repeat `--check`, and tamper rejection.
- Repository: Ruff format/check, MyPy, compile, focused/related/full tests, installed CLI, and
  `git diff --check`.

## Requirements traceability

| Requirement | Design mechanism | Primary verification |
|---|---|---|
| HICG-R1 | public identity grammar and public-only calibration inputs | private-path/input rejection tests |
| HICG-R2 | immutable upstream bindings and new namespace | exact SHA-256 and no-overwrite tests |
| HICG-R3 | one serialized graph/checksum before candidate comparison | same-checksum-across-candidates test |
| HICG-R4 | frozen context vocabulary with identity precedence | context and `Tesla Model S` regressions |
| HICG-R5 | local frame owners and conserved digit runs | multi-number and compact-frame tests |
| HICG-R6 | four enumerated numeric equivalences | positive equivalence plus unequal-digit rejection tests |
| HICG-R7 | unique prefix and alphabetic edit-1 relations | unique/ambiguous abbreviation and typo tests |
| HICG-R8 | primary-casting all-rank hard-conflict preflight | rank-1/secondary `R32/R33` versus `BNR34` tests |
| HICG-R9 | frozen categorical policy family | policy-order and source-order tests |
| HICG-R10 | casting/alias-only grammar and evidence | forbidden-field independence tests |
| HICG-R11 | immutable 223/22/24 historical calibration | exact denominator/gate contract tests |
| HICG-R12 | conditional `--freeze-protocol` branch | null/zero-retrieval stop tests |
| HICG-R13 | post-freeze deterministic 16+16 builder | family/style/non-reuse validators |
| HICG-R14 | label-blind raw and exactly-once collector | schema, call-count, and raw-reuse tests |
| HICG-R15 | complete evidence schema and immutable lifecycle | recomputation, `unchanged`, and tamper tests |
| HICG-R16 | isolated development module and promotion boundary | import/runtime/database no-change tests |

## Technical decisions and trade-offs

- A graph is chosen over another span because years, model numbers, context, and compact tokens need
  separate roles and local relations. The cost is more code and a larger evidence schema.
- Corpus-wide hypothesis selection is chosen over Top-5 candidate anchoring so candidate admission
  cannot rewrite the query. It may still choose the wrong public form for an ambiguous query; the
  graph keeps unresolved claims and calibration must catch that failure.
- Explicit context vocabulary plus identity-precedence is chosen over deleting all “noise” first.
  It is highly auditable but less semantically flexible than a learned classifier.
- Primary-casting conflict cannot be erased by aliases. This closes a structural bypass but may
  reject a document whose primary casting and alias genuinely encode different numbered models;
  such a corpus inconsistency must fail visibly rather than be silently selected.
- Bounded prefix/edit/OCR rules offer roughly a 10x auditability advantage over a cross-encoder:
  every transformation names its inputs, constraint, and reason. The trade-off is a valid null
  result if public variation exceeds those rules.
- The most likely failure is an ambiguous corpus-wide identity hypothesis that labels a genuine
  model word as context or assigns a digit to the wrong local slot. Exact positive gates and the
  no-new-retrieval historical branch gate expose this before another holdout is spent.

## Confirmation checkpoint

The owner confirmed this design and the subsequent task list before implementation. HICG-T1–T4
implement and verify the complete pre-holdout path. Formal historical calibration produced no
survivor, so the designed null branch persisted only calibration evidence with zero retrieval. No
protocol was authorized; pack materialization, collection, and selection are blocked. HICG-T8 now
closes and publishes the negative result without changing the frozen policies or claiming runtime
eligibility.
