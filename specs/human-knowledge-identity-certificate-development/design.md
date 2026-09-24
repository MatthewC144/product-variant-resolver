# Human Knowledge identity-certificate set v4 — Design

Date: 2026-09-24. Mode: Lite / Lean Industrial. Status: **CLOSED — historical FAIL; HICS-T6–T8 blocked; Pointwise/Listwise spec next**.

## Overview

HICG-v3 proved that one candidate-independent graph and all-rank numeric preflight are implementable,
but its policies still choose between two bad extremes. Candidate-residual symmetry rejects valid
partial names because a complete casting naturally contains words absent from the query. Removing
that restriction admits corpus-absent models after matching only a shared maker or generic token.

V4 replaces candidate-to-query completeness with a corpus-wide uniqueness proof. Before any
retrieved candidate is inspected, the system builds minimal identity certificates from the primary
casting of every public casting/family authority. A query produces a set of authority keys whose
complete certificate it satisfies. Candidate admission is then simple membership in a singleton
support set plus the existing all-rank primary-frame conflict veto.

This remains an offline public-development experiment. It does not alter retrieval, API behavior,
Dual RAG runtime, PostgreSQL, canonical identity, release promotion, or physical-feature handling.
After its branch-aware closure, work returns to the separately specified pointwise-versus-listwise
canonical reranking milestone; v4 failure does not authorize an automatic v5.

## Feasibility correction: authority keys, not document IDs

The committed Human Knowledge corpus contains 142 documents but only 139 resolvable casting/family
authorities:

- 100 provisional-variant documents map to 97 stable `casting_id` values;
- 42 review-family documents map to 42 stable `review_family_id` values;
- the duplicate-document excess is three, across `83 Chevy Silverado` and `Toyota Supra` casting
  groups.

The duplicate documents contain different provisional release/series details, but v4 is forbidden
from using those fields. Requiring a unique certificate per document would therefore be impossible
without leaking variant evidence. V4 defines these authority keys instead:

```text
casting:<casting_id>
review_family:<review_family_id>
```

Every candidate document maps to exactly one authority key. A singleton query support set may admit
multiple source candidates belonging to that same key, preserving source order and explicitly
reporting `casting_authority_only`. It never claims which provisional variant is correct.

## Architecture and branch order

```text
committed 142-document public corpus
                  |
                  v
      group into 139 authority keys
                  |
                  v
 derive casting-only minimal certificates
 and alias-to-casting claim bridges
                  |
                  v
 query -> candidate-independent support set
                  |
        empty / multiple / singleton
           |          |          |
           v          v          v
        abstain     abstain    membership +
                             primary-frame veto
                  |
                  v
 historical 223/22/24 calibration (0 retrieval)
                  |
       no survivor +-----------+ survivor
            |                              |
            v                              v
 persist null calibration       freeze source, inventory,
 and close v4                    policies, gates, protocol
                                             |
                                             v
                               family-disjoint 16+16 holdout
                                             |
                                             v
                               exactly-once Top-5 collection
                                             |
                                             v
                               frozen scoring or null winner
```

Implementation is isolated in
`src/product_variant_resolver/human_knowledge_identity_certificate_development.py`. Runtime modules
must not import it. Tests live in
`tests/evaluation/test_human_knowledge_identity_certificate_development.py`.

## Immutable upstream bindings

V4 validates prior evidence before constructing an inventory. The fixed bindings are:

| Upstream evidence | SHA-256 |
|---|---|
| HIC-v1 source | `167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f` |
| HIE-v2 source | `c91d8e253f1cd19cf59b626e794673defe2e28aea6c993cbce350d1698e83a5e` |
| HIE-v2 calibration JSON | `fbdc5171f3b1bfbe3f07b207acb56bd9608e2a3136bdff1acb9175e99f1557ce` |
| HIE-v2 calibration manifest | `03eee815b2cb4110e158f2ff02bf51d8b582282c1f050358c3be117ee238eeb5` |
| HIE-v2 calibration Markdown | `7e0fbd7e1f92cf0d043949e0c0fdee69bd4d53f0a9f40fe1a41d466f6b5039be` |
| HICG-v3 source | `998f5af0983517d5ead54cf5fddaf46a57056245f92ac6d0c00c3279260ab173` |
| HICG-v3 calibration JSON | `d2d94334d311c84e17c98b2f7d38876674ecf9def1c0dda6c889fbc822a7b1c2` |
| HICG-v3 calibration manifest | `9666ff2b5c63677fbc6f74daf9f4490e191c9a209151c798e44e75cccb2cac5f` |
| HICG-v3 calibration Markdown | `16f5b425c6c3e4f7947f868112663a1e024c0270484ebea34fcfe7f583b460a5` |

Every current corpus/evidence input and the v4 source are additionally hashed into v4 manifests. A
mismatch stops before inventory construction and writes nothing.

## Data model

### `IdentityAuthority`

```text
authority_key            casting:<id> | review_family:<id>
authority_kind           casting | review_family
primary_casting          normalized casting source
member_knowledge_ids     ordered tuple of one or more document IDs
member_knowledge_uuids   ordered tuple of one or more document UUIDs
approved_aliases         ordered, deduplicated match surfaces
status                   certifiable | unresolved_collision
```

For provisional documents, `human_label_names` are approved query match surfaces. Pricing keywords,
initial model text, series labels, variant labels, colors, release metadata, and source IDs are not
certificate inputs. Review-family aliases remain approved match surfaces. Member order is lexical by
knowledge ID and cannot influence certificate selection.

### `CertificateClaim`

```text
claim_id                 stable position-derived ID
kind                     alphabetic | numeric_frame | alphanumeric_frame
normalized_value         normalized primary-casting value
source_atom_indices      ordered primary-casting positions
frame_kind               leading_year | standalone_model | alphanumeric_model | compact_model | null
owner_before/after       adjacent primary identity atoms or null
digit_runs               exact conserved digit runs
```

A local frame is one indivisible claim. Its digits cannot be consumed by an alphabetic claim or
moved to another owner slot.

### `IdentityCertificate`

```text
certificate_id           SHA-256-derived stable ID
authority_key            exactly one authority
claim_ids                ordered, nonempty subset of primary-casting claims
primary_casting          source form
member_knowledge_ids     disclosure of document grouping
competing_before         all other authority keys
elimination_steps        remaining competitors after each ordered claim
remaining_after          exactly the target authority key
minimality_proof         every one-claim deletion loses uniqueness
checksum                  canonical JSON SHA-256
```

### `AliasBridge`

An alias may map query spans to an existing primary-casting claim. Each bridge records alias source
positions, target claim IDs, relation names, unmapped alias atoms, and checksum. It cannot add a
certificate claim, change digits, merge two authorities, or use variant/release fields.

### `QuerySupportEvidence`

```text
normalized_query
inventory_checksum
profile_id
query_atoms + source offsets
context_atoms + reason codes
certificate_matches
support_authority_keys
ambiguous_authority_keys
unresolved_discriminative_atoms
numeric_conflicts
status                    singleton | empty | ambiguous | error
checksum
```

Candidate evidence adds its authority key, source rank, primary-frame comparison, membership result,
decision, and reason codes. The query evidence and checksum are identical across all candidates.

## Certificate inventory construction

### 1. Group documents without collapsing releases

The builder loads the validated 142-document public catalog, maps every document to one authority
key, and requires exactly 139 current keys. Source documents remain separate; grouping only defines
which casting/family identity they share. A document cannot appear in two groups.

### 2. Derive claims only from primary casting

The primary casting is normalized, atomized, and split into local numeric/alphanumeric frames using
the frozen v3 structural grammar. Current primary casting names contain at most eight normalized
tokens. V4 permits at most twelve primary claims per authority; exceeding that bound is an inventory
error requiring a new version, not silent truncation.

Aliases are deliberately excluded from certificate derivation. This prevents a human label such as
a long series/color title from making release metadata appear to be casting identity. Aliases are
processed later only as bounded bridges to existing primary claims.

### 3. Enumerate minimal ordered subsets

For each primary casting, the builder enumerates all nonempty ordered subsets of its at-most-twelve
claims in increasing subset size. A subset distinguishes the target only when no other authority's
primary casting contains an equivalent ordered claim sequence with the same numeric-frame owners and
digit runs.

A one-claim alphabetic certificate is valid only when the target primary casting itself contains
exactly that one identity claim. This prevents a maker-only subset such as `Honda` from certifying
`Honda Civic EG`, while preserving genuine one-word casting identities. Numeric/alphanumeric
one-claim certificates retain their complete local frame and owner proof.

The builder keeps a subset only when removing any one claim makes it lose admissible uniqueness. A
deletion can fail because it becomes non-unique, empty, or the forbidden one-alphabetic-claim form
for a longer primary casting; the proof records which condition occurred. It then removes duplicate
certificates and orders results by claim count, non-alphabetic frame count, normalized claim tuple,
and certificate ID. If even the complete primary casting is not unique across authority keys, that
authority is `unresolved_collision` and ineligible.

### 4. Prove minimality and bind bytes

Each certificate serializes all competing keys before matching and the remaining set after every
claim in canonical claim order. Validation independently recomputes uniqueness and every one-claim
deletion. The inventory serializes all 139 authorities, certificate/bridge records, rule versions,
input hashes, and a canonical JSON checksum.

## Query normalization and certificate matching

### One query parse before candidates

The matcher normalizes and tokenizes the complete query once, retaining original/normalized offsets.
It uses the entire frozen inventory rather than Top-5 candidates. Compact segmentation searches
only primary claims, approved alias bridges, and context vocabulary; it cannot delete or reorder a
digit run.

### Frozen context vocabulary

V4 begins with the committed `IdentityCorePolicy.NOISE` vocabulary and HICG-v3 context extension.
It adds the general public wrappers `unverified`, `greetings`, `space`, `premium`, `performance`,
`hypercar`, `sedan`, `coupe`, `roadster`, `electric`, `crossover`, `wagon`, and `touring`.

Identity participation always wins over context membership. For example, a word used by a primary
casting claim cannot be discarded as context in that certificate comparison. The vocabulary and
precedence rule are serialized before historical scoring; later additions require a new version.

### Matching profiles

V4 freezes three non-reference profiles plus one non-surviving reference:

| Profile | Allowed certificate relations |
|---|---|
| `reference-anchor` | Existing rank-1/secondary behavior; comparison only, never a survivor |
| `certificate-exact` | Exact normalized primary claims and equal local frames |
| `certificate-structural` | Exact plus punctuation/spacing, compact segmentation, and leading-year suffix |
| `certificate-bounded` | Structural plus unique prefix, alpha edit-1, same-frame `o/0`, repeated-digit restoration, and leading-year uncertainty `x` |

Every non-reference profile requires a complete certificate, conserved query order, distinct query
spans for distinct claims, no unresolved discriminative query atom, and no conflicting local frame.
There is no scalar similarity or coverage threshold.

### Residual and ambiguity rules

After a certificate match, unmatched context atoms are retained with reason codes but do not veto.
Every other unmatched alphabetic or numeric atom is `unresolved_discriminative` and removes that
authority from the support set. This is how `Honda Accord` fails even if `Honda` appears in the
corpus, while a query with a complete `55 Chevy` certificate plus `unverified listing` can survive.

All matching certificates are collapsed by authority key. Zero supported keys produces `empty`;
more than one produces `ambiguous`; exactly one produces `singleton`. The matcher never chooses one
key through source rank, retrieval score, knowledge UUID, or lexical tie-break.

## Candidate membership and conflict preflight

For an empty or ambiguous support set, every candidate abstains. For a singleton support set, a
candidate can proceed only when its precomputed authority key equals the singleton key.

The primary casting is then compared with the query's conserved numeric/alphanumeric frames. An
unequal comparable digit claim fails at ranks 1–5 even when an approved alias omits it. Because
authority membership already supplies structural identity evidence, v4 does not apply the old
secondary `>=0.75` token-coverage shortcut.

Candidate order never changes. Multiple documents under the one supported casting authority may be
admitted in their original source positions, with `casting_authority_only` and
`variant_not_resolved` reason codes. No candidate from another authority may remain.

## Historical calibration and selection

The calibration command rescans only immutable public evidence:

```text
223 existing development rows
22 anchor-confidence v4 rows
24 HIC-v1 rows
0 retrieval calls
```

Every non-reference profile must satisfy every prior positive, merge, governance, unrelated-output,
required-target, absent-identity, and secondary BNR34 gate. It must also have zero retrieval,
inventory, query-support, alias-alignment, frame-comparison, and decision errors.

The reference profile cannot survive. Eligible profiles are ordered by:

1. fewer admitted candidates across negative cases;
2. fewer abstained source candidates across positive/regression cases;
3. fewer non-exact equivalence operations;
4. least-permissive relation order: `certificate-exact`, `certificate-structural`, then
   `certificate-bounded`.

If none survives, v4 writes only calibration JSON, manifest, and Markdown with `winner: null`, then
closes. It creates no protocol, pack, raw, selection, private evaluation, or runtime change.

## Conditional public holdout

Only a historical survivor authorizes protocol/source/inventory freeze and a new 16+16 holdout.
Positive cases use sixteen distinct public authorities/documents unused by the v4/HIC positive
packs, four each for:

- unique partial certificate;
- punctuation/compact certificate;
- bounded edit/abbreviation certificate;
- year/numeric certificate.

Negative declarations are authored only after freeze and contain four cases each for:

- shared-maker incomplete certificate;
- same-maker model substitution;
- numeric/alphanumeric frame conflict;
- ambiguous certificate/context overlap.

Every negative query/identity must be corpus-absent and must not repeat earlier negative packs. The
32 queries are retrieved once at Top 5. Label-blind raw bytes are persisted before labels are joined,
and every surviving profile reuses the same bytes. Retrieval errors are retained without retry.

Holdout eligibility requires 16/16 positive hits, 0/16 negative nonempty results, zero computation
errors, and all historical gates. Passing qualifies a winner only for a separately specified private
shadow evaluation; it does not activate runtime.

## Interfaces and artifact lifecycle

The installed command will be `pvr-develop-human-knowledge-identity-certificate`:

```text
--freeze-protocol   build inventory and historical calibration; freeze only on survivor
--freeze-pack       create/validate the family-disjoint 16+16 pack; no retrieval
--collect           execute exactly 32 Top-5 calls once and persist label-blind raw rows
--score             join frozen labels and persist deterministic selection once
--check             recompute/validate current artifacts; no retrieval and no writes
```

Namespaces are new and never overwrite v1–v3:

```text
specs/human-knowledge-identity-certificate-development/
  requirements.md
  design.md
  tasks.md
  holdout-negative-declarations.json          # only after historical PASS

data/evaluation/human-knowledge-identity-certificate-development-v4/
  protocol/protocol.json
  protocol/protocol-manifest.json
  pack/development-pack.json
  pack/development-pack-manifest.json
  raw/raw.json
  raw/raw-manifest.json

reports/human-knowledge-identity-certificate-development-v4/
  historical-calibration.json
  historical-calibration-manifest.json
  historical-calibration.md
  selection.json
  selection.md
```

Existing complete artifacts are independently recomputed and returned as `unchanged`. Partial,
extra, stale, or byte-different artifacts fail closed and are never overwritten. From successful
protocol freeze onward, source, inventory, profiles, context/equivalence rules, gates, protocol, and
declarations schema are immutable through closure.

## Error handling

- Missing, malformed, reordered, duplicate, stale, or hash-mismatched public evidence stops before
  writes.
- A document in two authorities, authority/member drift, more than twelve primary claims, duplicate
  certificate IDs, an invalid minimality proof, or a certificate unique only through alias/release
  fields is an inventory error.
- Candidate-dependent support changes, reused query spans, moved/deleted digits, unknown relations,
  conflicting alias bridges, or a primary conflict hidden by an alias is a computation error.
- Empty and ambiguous support sets are valid abstentions, not exceptions.
- Historical denominator/gate drift stops before protocol or retrieval.
- Pack imbalance/reuse, labels in raw rows, a call count other than 32, or any frozen-byte change
  invalidates the downstream phase.
- A defect found after freeze preserves evidence and closes v4; it does not authorize in-place repair
  or v5.

## Security and privacy notes

Historical development reads only committed public files and needs no network, browser, credential,
dynamic code, external model, or new runtime dependency. Private five-family projection paths and
results are forbidden inputs. Raw holdout rows exclude expected labels, decisions, gates, and winner
fields. Query/candidate limits reuse existing bounded retrieval contracts.

## Testing strategy

- Inventory unit tests: 142 documents map exactly once to 139 authority keys; the two multi-document
  casting groups remain grouped without variant claims; complete primary castings are unique;
  certificates are minimal, deterministic, and casting-derived only.
- Certificate regressions: manufacturer-only partials cannot certify a multi-token casting; valid
  one-word castings can; supersets are removed; ordered claims and local frame owners are conserved.
- Alias boundary tests: approved aliases can bridge to primary claims but cannot contribute series,
  color, release, provenance, or another authority's claims.
- Positive query tests: `55 Chevy`, compact `fishdchipd`, `x34landspeeder`,
  `kowloondhypervan`, bounded `kick kat`, year/OCR/repeated-digit/uncertainty forms, and general
  context wrappers.
- Negative query tests: `Honda Accord`, `BMW M4`, `Bugatti Divo`, Tesla model substitutions,
  manufacturer-only input, empty/ambiguous certificates, and rank-1/secondary `R32/R33` versus
  `BNR34`.
- Candidate tests: singleton membership, cross-authority rejection, same-authority multi-document
  preservation, alias non-bypass, source-order stability, and explicit variant non-resolution.
- Contract tests: exact 223/22/24 denominators/gates, zero historical retrieval, conditional
  protocol, 16+16 pack, exactly-once collection, label-blind raw schema, and phase ordering.
- Artifact tests: source/inventory/protocol/pack/raw hashes, repeat `unchanged`, null branch, winner
  ordering, tamper/partial-state rejection, and absence of downstream effects after failure.
- Repository checks: targeted Ruff format/check, target-local MyPy, compileall, focused/related/full
  tests, installed CLI, repeated integrity checks, and staged `git diff --check`.

## Requirements traceability

| Requirement | Design mechanism | Primary verification |
|---|---|---|
| HICS-R1 | committed public loaders and forbidden private path boundary | input/source manifest tests |
| HICS-R2 | fixed v1–v3 SHA-256 bindings and new namespace | mismatch/no-overwrite tests |
| HICS-R3 | 139 authority groups and casting-only minimal subsets | grouping/minimality/collision tests |
| HICS-R4 | certificate provenance, elimination steps, and checksum | independent minimality recomputation |
| HICS-R5 | one inventory-wide query support pass before candidates | same support checksum across candidates |
| HICS-R6 | complete-certificate and single-claim eligibility rules | shared-maker negative regressions |
| HICS-R7 | certificate proof ignores unmatched candidate-name suffixes | valid partial-name regressions |
| HICS-R8 | three frozen relation profiles and frame conservation | positive equivalence/unequal-digit tests |
| HICS-R9 | unresolved veto plus empty/ambiguous fail-closed states | substitution/ambiguity regressions |
| HICS-R10 | frozen context vocabulary with identity precedence | context-versus-identity tests |
| HICS-R11 | singleton authority membership and primary conflict preflight | membership/BNR34/multi-document tests |
| HICS-R12 | primary casting claims and bounded alias bridges only | forbidden-field independence tests |
| HICS-R13 | immutable zero-retrieval 223/22/24 calibration | exact denominator/gate tests |
| HICS-R14 | conditional freeze and deterministic null branch | no-survivor/no-downstream tests |
| HICS-R15 | frozen 16+16 protocol and exactly-once lifecycle | pack/raw/hash/tamper tests |
| HICS-R16 | complete support/candidate evidence and isolated module | evidence schema/runtime no-change tests |

## Technical decisions and trade-offs

- Authority grouping is chosen over document-level certificates because identity-only evidence cannot
  distinguish multiple provisional releases of one casting. This preserves truth at the cost of no
  variant-level claim.
- Certificates come only from primary castings; aliases are bridges. This prevents series/color text
  embedded in human labels from becoming uniqueness evidence, but may reduce recall for an alias
  whose relationship to the casting cannot be structurally proven.
- Exhaustive subset enumeration is acceptable because current primary castings contain at most eight
  tokens and the frozen safety cap is twelve. It supplies direct minimality proof rather than a
  heuristic score, at the cost of requiring a new version if future casting names exceed the cap.
- Unmatched discriminative query atoms veto support, while unmatched candidate suffixes do not. This
  directly targets v3's recall/safety boundary, but context classification remains the main failure
  risk and is therefore frozen and audited.
- Three categorical relation profiles are chosen instead of another tuned threshold. This keeps the
  result explainable but may again produce a valid null winner.
- The approximately 10x auditability advantage over a neural admission model is the ability to show
  the exact minimal claims, eliminated competitors, alias bridge, residual veto, and membership proof
  for every decision.
- The most likely failure is that a query's legitimate wrapper remains unresolved or a bounded alias
  bridge cannot prove enough primary claims. Historical exact gates expose this at zero retrieval.

## Confirmation checkpoint

The owner confirmed on 2026-09-23 that v4 should be completed before returning to the original
pointwise-versus-listwise milestone, with v4 treated as the last bounded identity-admission attempt.
This design adds the required 142-document/139-authority correction and remains a draft. No task list,
source, artifact, retrieval, private evaluation, API, Dual RAG, PostgreSQL, canonical, release, or
physical-feature change is authorized until the owner confirms this design.
