# Human Knowledge query-global identity envelope — Design

Date: 2026-09-21. Mode: Lite / Lean Industrial. Status: **HIE-T3 historical calibration FAIL; no protocol frozen**.

## Overview

HIC v1 lets each query-candidate pair choose its own best query span. That is auditable, but two
public failures show that the freedom is unsafe: `88` and `1988` become a false bilateral residual,
while a wrong `R33`/`BNR34` comparison can omit the decisive digits from the chosen span.

V2 constructs one query-global identity envelope before evaluating any retrieved candidate. Every
candidate sees the same normalized atoms and offsets. The decision layer then uses categorical
numeric relations and unmatched model evidence rather than selecting another scalar residual
threshold.

This remains an offline public-development experiment. It does not change retrieval, the API, or
the Dual RAG runtime.

## Architecture and freeze order

```text
committed public corpus + existing 223/v4-22/HIC-v1-24 evidence
                               |
                               v
       implement envelope + structural policies without new holdout
                               |
                               v
       historical calibration gate (no retrieval; at least one survivor)
                               |
                               v
       freeze source + protocol + holdout-selection rules first
                               |
                               v
       materialize new family-disjoint 16+16 holdout pack
                               |
                               v
       retrieve 32 queries once and persist label-blind raw bytes
                               |
                               v
       score historical evidence + untouched new holdout
                               |
                               v
                    deterministic winner or null
```

The protocol is intentionally frozen before the new holdout pack is materialized. Positive
selection is deterministic, and negative declarations are not added until the source hash and all
policy rules are immutable. This prevents changing the envelope or decision list after seeing the
new 32-case outcomes.

Implementation will be isolated in
`src/product_variant_resolver/human_knowledge_identity_envelope_development.py`. Runtime modules must
not import it. HIC-v1 files remain read-only upstream evidence.

## Public calibration and untouched holdout

### Historical calibration

Before protocol freeze, candidate policies may be evaluated only against committed public evidence:

- the existing 223-row development evidence;
- anchor-confidence v4's 22 rows;
- HIC-v1's 24 rows.

At least one non-reference policy must satisfy every historical gate before v2 spends 32 new
retrieval calls. If none does, the process stops before protocol/pack freeze and records the failed
calibration. Historical evidence is for policy construction; it is not called a new holdout.

### New holdout

After protocol and source freeze, the pack builder selects sixteen positive cases from documents not
used by v4 or HIC-v1 positives. It uses four documents per challenge style and exactly one case per
document. Deterministic ordering is by a protocol-bound SHA-256 selection key, not filesystem or
dictionary order.

Sixteen new absent identities are then declared with four cases in each category:

1. same-maker different-model text;
2. conserved numeric or alphanumeric-frame conflict;
3. compact/punctuation form that must retain its digits;
4. cross-maker descriptor overlap.

Every identity and normalized query must be absent from all corpus casting/alias forms and from all
v4/HIC-v1 negative declarations. Pack validation rechecks these properties from source bytes.

## Query-global envelope algorithm

### 1. Normalize and atomize once

Use the existing `IdentityCorePolicy` and HIC atom representation. Each atom retains normalized
text, source token, character offsets, alphabetic/numeric kind, and alphanumeric-frame membership.
The query is normalized once per raw row, not once per candidate.

### 2. Build a public anchor index

For every casting and approved alias in the 142-document corpus:

- ignore an optional leading two- or four-digit numeric atom;
- record the first remaining alphabetic atom as a possible identity anchor;
- retain the full ordered form and document frequency;
- never read series, release year, color, or other metadata.

For each occurrence of an anchor atom in the query, compare the surrounding query atoms with every
public form only to score the anchor location. This corpus-wide search is independent of the actual
Top-5 candidates. Anchor choice first maximizes explained public-form IDF proportion, then matched
IDF, then ordered similarity, then prefers the later start so leading marketplace context is not
absorbed, and finally uses lexical form order for determinism.

### 3. Form one envelope

The envelope starts at the selected anchor, except that one immediately preceding two- or
four-digit atom is included as a possible leading identity year. It ends at the last non-noise atom
remaining after the existing identity-core policy. All unknown alphabetic or numeric atoms between
those boundaries remain in the envelope; they cannot be removed because one candidate does not
explain them.

If no anchor exists, the entire identity core becomes an `unanchored` envelope. No policy may invent
a candidate-specific replacement span. The same envelope object and checksum are attached to every
candidate evaluation for the row.

### 4. Preserve numeric frames

Alphanumeric source tokens retain a frame record such as:

```text
R33    -> alphabetic skeleton `r`, digits `33`
BNR34  -> alphabetic skeleton `bnr`, digits `34`
MX-5   -> alphabetic skeleton `mx`, digits `5`
```

Compact/fuzzy alignment may align alphabetic material but cannot consume a digit run unless the
candidate digit run is equal or a declared shorthand equivalence. Any envelope or candidate digit
left outside the chosen atom alignment remains explicit evidence.

### 5. Allow one structural shorthand

A two-digit leading token and four-digit leading candidate token are `year_suffix_equivalent` only
when:

- both precede the same aligned identity anchor;
- the four-digit token begins with `19` or `20`;
- its final two digits equal the two-digit token;
- neither token belongs to another alphanumeric model frame.

The inverse direction is allowed under the same checks. This is a general token rule, not a release
year lookup or casting exception. `88`/`1988` qualifies; `R33`/`R34` and `M2`/`M4` do not.

### 6. Derive categorical evidence

Each candidate receives these bounded states:

```text
envelope_status          anchored | unanchored
anchor_relation          equal | different | unavailable
numeric_relation         none | equal | year_suffix_equivalent | conflict | query_only | candidate_only
form_completion          complete | partial
alignment_strength       exact | shorthand | fuzzy | weak
query_model_residual     none | present
candidate_model_residual none | present
compact_digit_guard      pass | fail
```

Model residuals exclude zero-weight single-character fragments but retain unknown words and all
conserved numeric/alphanumeric-frame atoms. No floating residual threshold is itself a policy.

## Frozen policy family

Ranks 2–5 always keep the existing identity-token coverage `>= 0.75` gate. Rank 1 is compared under
five predeclared policies:

| Configuration | Ordered rank-1 rule |
|---|---|
| `reference-anchor` | Admit rank 1; comparison only |
| `envelope-numeric` | Reject numeric conflict or compact-digit-guard failure; otherwise admit |
| `envelope-bilateral` | Numeric rule, then reject different anchors or residual model evidence on both sides; otherwise admit |
| `envelope-safe-form` | Numeric rule; admit complete exact/shorthand forms; reject different anchors or any remaining query model residual; otherwise admit |
| `envelope-decision-list` | Numeric rule; admit complete exact/year-equivalent forms; reject anchor mismatch; admit one bounded fuzzy form only with no model residual; reject bilateral model residual; otherwise abstain as ambiguous |

The reference policy may be reported but cannot win unless it independently meets every gate.
Policy definitions, rule order, allowed states, and tie-breaking are serialized in the protocol.

## Historical calibration gate

Before freezing source/protocol, each policy is applied to the existing 223, v4 22, and HIC-v1 24
rows. A non-reference policy survives only if it preserves every historical positive/merge/required
target, emits zero historical forbidden/unrelated/absent-identity results, and has zero computation
errors. If no non-reference policy survives, v2 stops without creating the new pack or retrieval.

Surviving policies are all frozen; the new holdout result chooses among them without changing their
rules.

## Winner ordering

Eligibility requires every historical and new HIE-R11 gate. Among eligible policies, choose:

1. fewer admitted candidates across all v4/HIC-v1/new negative cases;
2. fewer abstained candidates across all positive and regression cases;
3. the less restrictive explicit order `envelope-numeric`, `envelope-bilateral`,
   `envelope-safe-form`, `envelope-decision-list`.

A null winner is valid and authorizes no next stage.

## Interfaces and artifact lifecycle

The installed command will be `pvr-develop-human-knowledge-identity-envelope`:

```text
--freeze-protocol   validate historical calibration, then bind source/rules/hashes; no retrieval
--freeze-pack       materialize/validate the 16+16 holdout under the frozen protocol; no retrieval
--collect           make exactly 32 Top-5 calls and persist label-blind raw rows once
--score             join frozen labels after raw persistence and write selection artifacts once
--check             recompute and validate all public artifacts; no retrieval or writes
```

Invalid phase order fails closed. From protocol freeze onward, the development source cannot change.

```text
specs/human-knowledge-identity-envelope-development/
  holdout-negative-declarations.json   # authored only after protocol/source freeze
data/evaluation/human-knowledge-identity-envelope-development-v2/
  protocol/protocol.json
  protocol/protocol-manifest.json
  pack/development-pack.json
  pack/development-pack-manifest.json
  raw/raw.json
  raw/raw-manifest.json
reports/human-knowledge-identity-envelope-development-v2/
  selection.json
  selection.md
```

Raw rows contain queries, source-ranked candidates, retrieval work, and errors but no expected
labels or admission decisions. Every manifest binds exact source and upstream artifact SHA-256
values. The protocol freezes the declarations schema and fixed path but not its future contents.
After protocol freeze, `--freeze-pack` reads that file, validates all sixteen declarations, and
binds its exact hash in the pack manifest; no product source change is permitted.

## Error handling

- A historical calibration failure stops before protocol freeze or new retrieval.
- Missing, partial, reordered, stale, or hash-mismatched artifacts fail closed.
- Duplicate cases, reused prior documents/identities, corpus-present negatives, wrong ranks,
  envelope differences between candidates, omitted conserved digits, invalid shorthand, unknown
  states/reasons, nonfinite values, or denominator drift are errors.
- Per-query retrieval errors are stored and never retried or removed; every policy becomes
  ineligible.
- A post-freeze source defect preserves v2 artifacts and requires a new version.

## Security and privacy notes

All development inputs are committed public data. No browser, network, credential, external model,
private path, or dynamic code execution is required. Existing query/token bounds remain in force.
The new holdout and its raw rows are public development evidence, not a private final test.

## Testing strategy

- Unit: anchor-index construction, single envelope per query, offsets, leading-year inclusion,
  numeric-frame conservation, shorthand equivalence and rejection, categorical states, policy
  ordering, and source-order preservation.
- Contract: historical calibration before freeze, 16+16 pack, 16 unused documents, balanced styles,
  negative absence/non-reuse, exactly 32 calls, label-blind raw schema, source hashes, and immutable
  phase order.
- Adversarial: `88`/`1988` preservation, `R33`/`R34` and `R33`/`BNR34` rejection, compact digit
  swallowing, leading context before the anchor, trailing marketplace noise, unanchored input, and
  multiple possible anchors.
- Artifact: all historical/new denominators, deterministic winner/null, tamper rejection, and
  repeated `--check`.
- Repository: Ruff/format, MyPy, compile, focused/related/full tests, installed CLI, and
  `git diff --check`.

## Technical decisions and trade-offs

- A query-global envelope is chosen over candidate-specific spans because all candidates must answer
  the same identity claim. It may be less flexible for unusual word order, so unanchored and
  multiple-anchor behavior is explicit and tested.
- Categorical numeric relations are chosen over another residual threshold because the public
  failures are structural: omitted digits and legitimate shorthand are different states, not merely
  different score magnitudes.
- Historical calibration precedes the new holdout to avoid spending retrieval calls on a policy
  already known to fail. Protocol-before-pack freeze prevents code changes after the exact new cases
  become visible.
- Deterministic rules retain roughly a 10x auditability advantage over a cross-encoder: every reject
  can name the envelope, conserved atoms, relation, and rule branch. The cost is lower semantic
  coverage and a real possibility that no rule survives historical calibration.
- The most likely failure is an identity whose leading atom is not a reliable manufacturer/model
  anchor, causing the global envelope to include context or miss a reordered identity. The
  calibration gate and new family-disjoint holdout test this before any private evaluation.

## Confirmation checkpoint

The owner confirmed this design before the task list and implementation. HIE-T1 now implements only
the unfrozen primitives; policies, protocol, pack, retrieval, and scoring remain later ordered tasks.
