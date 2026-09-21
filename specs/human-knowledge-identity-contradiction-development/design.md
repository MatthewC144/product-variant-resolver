# Human Knowledge candidate-specific identity contradiction — Design

Date: 2026-09-21. Mode: Lite / Lean Industrial. Status: **owner confirmed; implementation complete**.

## Overview

The v4 scalar experiment asked whether a candidate looked similar enough. This design asks a
different question: after aligning the candidate's best casting or approved alias to the most likely
identity span in the query, does each side still contain incompatible model evidence?

The experiment remains an offline public-development tool. It adds no runtime dependency and does
not change retrieval. A candidate is first retrieved by the frozen Human Knowledge v4 retriever;
the proposed layer only decides whether that already-ranked candidate may be emitted.

## Architecture

```text
committed public corpus + public development artifacts
                         |
                         v
          build/freeze new 12+12 public pack
                         |
                         v
        freeze alignment rules + policy grid + gates
                         |
                         v
       retrieve 24 new queries exactly once (Top 5)
                         |
              persist label-blind raw.json
                         |
                         v
  query span selection + ordered one-to-one identity alignment
                         |
       numeric conflict + bilateral residual evidence
                         |
   rescore public 223 + v4 22 + new 24 without retrieval
                         |
              deterministic winner or null
```

Implementation is isolated in
`src/product_variant_resolver/human_knowledge_identity_contradiction_development.py`. It may import
the frozen identity normalizer, token matcher, v3 secondary admission, and v4 validators, but the
runtime resolver must not import this development module.

## Pack design

The new pack contains exactly 24 cases and is frozen before the protocol or retrieval.

### Positive-preservation cases

Twelve cases are selected deterministically from the existing public positive pack and already
committed raw rows. Selection excludes every v4 anchor-positive source case and requires a correct
source-rank-1 target. Cases span at least ten documents and cover single-edit, abbreviation/numeric,
spacing/punctuation, and contextual-noise styles. This is public development evidence, not a final
holdout.

### Absent-identity contradiction cases

Twelve newly authored identities must be absent from every normalized casting and approved alias.
The protocol uses four challenge types with three cases each:

1. `same_maker_model_substitution` — manufacturer token agrees but model tokens differ;
2. `same_stem_numeric_conflict` — model stem agrees but a meaningful model number differs;
3. `compact_or_punctuated_conflict` — misleading compact or punctuation form still names another
   model;
4. `cross_maker_descriptor_overlap` — generic performance/body-style wording overlaps while the
   manufacturer or model conflicts.

The negative query must contain its declared absent identity after normalization. No identity or
query from v4's twelve negative cases may be repeated.

## Identity-span algorithm

### 1. Normalize and atomize

Use `IdentityCorePolicy` to remove the already frozen marketplace noise. Split remaining text into
ordered alphabetic and numeric atoms while retaining each atom's source token and offsets. Examples:
`R32` becomes `r` + `32`; `MX-5` becomes `mx` + `5`; compact text still retains its original span.

Single-character alphabetic atoms have zero residual weight unless they belong to an alphanumeric
model frame. This prevents isolated punctuation fragments from becoming contradiction evidence.

### 2. Candidate forms and query windows

Candidate forms are only `casting` plus approved `aliases`. For every form, enumerate contiguous
query windows from `max(1, candidate_atom_count - 2)` through `candidate_atom_count + 2`. Limits are
bounded by the frozen 64-token query limit; no unbounded combinatorial search is introduced.

### 3. Ordered one-to-one alignment

Dynamic programming aligns atoms without crossing or reusing an atom. Match modes, in descending
priority, are:

- exact normalized atom;
- existing prefix abbreviation with a minimum two-character prefix;
- existing atomic `SequenceMatcher` ratio at least `0.8`;
- compact groups of one to four consecutive atoms on either side with compact character ratio at
  least `0.85`, provided their digit runs are identical after an allowed OCR substitution.

An OCR-only substitution of `o` for `0` or `i`/`l` for `1` is allowed inside a compact group when
that substitution makes the group exact. It is recorded as `ocr_numeric_substitution`, not silently
treated as exact.

The selected form/window first maximizes the proportion of candidate IDF weight explained by the
alignment, then maximizes absolute matched candidate weight. Remaining ties prefer a query-window
atom count closest to the candidate form, greater alignment similarity, the longer span, earlier
start offset, and lexical form order. This prevents the selector from hiding a contradiction by
choosing only a shared manufacturer token such as `Honda`.

### 4. Residual weights

Identity-document frequency is computed only from the 142 public documents:

```text
idf(atom) = log((document_count + 1) / (document_frequency + 1)) + 1
weight(atom) = idf(atom) / max_public_idf
```

An unmatched query atom absent from the identity vocabulary receives weight `1.0`. Matched atoms and
existing `IdentityCorePolicy` noise receive zero residual weight. For the selected alignment:

```text
query_residual = sum(unmatched identity-bearing query atom weights)
candidate_residual = sum(unmatched candidate atom weights)
bilateral_residual = min(query_residual, candidate_residual)
```

Using the minimum is intentional: extra seller wording alone or an optional candidate prefix alone
cannot create a contradiction; both sides must assert different identity material.

### 5. Numeric conflict

A numeric conflict is emitted before fuzzy similarity can hide it when aligned alphanumeric frames
have the same alphabetic skeleton but different digit runs, such as `R32` versus `R34` or `M4`
versus `M1`. The declared OCR substitutions above are not conflicts. Different standalone numbers
without the same model frame are not sufficient by themselves; they remain residual evidence and
must be accompanied by bilateral identity disagreement. This avoids treating an incidental listing
year as a model conflict.

## Frozen policy grid

Rank 1 is tested with seven configurations. Ranks 2–5 always retain the v3 coverage `>= 0.75` gate.

| Configuration | Rank-1 abstention rule |
|---|---|
| `baseline-anchor` | never abstain from rank 1 |
| `numeric-only` | numeric conflict |
| `contradiction-050` | numeric conflict OR bilateral residual `>= 0.50` |
| `contradiction-075` | numeric conflict OR bilateral residual `>= 0.75` |
| `contradiction-100` | numeric conflict OR bilateral residual `>= 1.00` |
| `contradiction-125` | numeric conflict OR bilateral residual `>= 1.25` |
| `contradiction-150` | numeric conflict OR bilateral residual `>= 1.50` |

The grid is deliberately small and interpretable. It tests candidate-specific contradiction
strength rather than another similarity confidence. After protocol freeze, no threshold, noise word,
match mode, weight, or exception may change based on results.

## Interfaces

The installed command will be `pvr-develop-human-knowledge-identity-contradiction` with mutually
exclusive phases:

```text
--freeze-pack       create or byte-check pack and manifest; no retrieval
--freeze-protocol   create or byte-check protocol and manifest; no retrieval
--collect           make exactly 24 retrieval calls and persist label-blind raw.json once
--score             read frozen raw + labels, write selection JSON/Markdown once
--check             recompute and validate every committed public artifact; no retrieval
```

Invalid phase order fails closed. `--score` cannot collect; `--check` cannot write or retrieve.

## Data models

### Alignment evidence

Each candidate record adds:

```text
candidate_identity
candidate_identity_kind          casting | alias
query_span_text
query_span_start / query_span_end
alignments[]                     query atoms, candidate atoms, mode, similarity
unmatched_query_atoms[]          atom, weight, offsets
unmatched_candidate_atoms[]      atom, weight
query_residual
candidate_residual
bilateral_residual
numeric_conflict                 bool
reason_codes[]
decision                         admit | abstain
```

Allowed reason codes are frozen: `no_contradiction`, `numeric_model_conflict`,
`bilateral_identity_residual`, and `secondary_coverage_below_075`. OCR substitution is alignment
metadata, not an admission reason.

### Artifact layout

```text
data/evaluation/human-knowledge-identity-contradiction-development-v1/
  pack/development-pack.json
  pack/development-pack-manifest.json
  protocol/protocol.json
  protocol/protocol-manifest.json
  raw/raw.json
  raw/raw-manifest.json
reports/human-knowledge-identity-contradiction-development-v1/
  selection.json
  selection.md
```

Every manifest binds source and artifact SHA-256 values. Raw rows contain queries and retrieved
public candidates but no expected label fields. Scoring joins labels only after raw persistence.

## Winner ordering

Eligibility requires every HIC-R8 gate. Among eligible policies, choose in order:

1. fewer total admitted candidates across the 24 v4/new negative cases;
2. fewer abstained candidates across all positive/regression cases;
3. less aggressive policy in the explicit order `numeric-only`, `contradiction-150`,
   `contradiction-125`, `contradiction-100`, `contradiction-075`, `contradiction-050`.

`baseline-anchor` can be reported but cannot win unless it independently meets every zero-negative
gate. A null winner is a valid experiment result.

## Error handling

- Missing, partial, reordered, stale, or hash-mismatched frozen artifacts raise an error.
- Duplicate case IDs, repeated v4 identities, corpus-present negative identities, wrong source rank,
  denominator drift, unknown reason codes, nonfinite scores, reused alignment atoms, or invalid
  offsets fail closed.
- A per-query retrieval error is preserved in raw evidence and makes every policy ineligible; the
  experiment does not retry that query or silently drop it.
- A scoring failure never overwrites raw evidence.

## Security and privacy notes

All inputs are local committed public data. No network, browser, credential, external model, private
path, or dynamic code execution is needed. Query/token bounds already enforced by Human Knowledge v4
remain in effect. Raw output is public-development evidence and must contain no private local source.

## Testing strategy

- Unit tests: atomization, offsets, exact/prefix/fuzzy/compact alignment, OCR substitution, numeric
  conflict, IDF weights, bilateral residual, tie-breakers, source-order preservation, and reason
  codes.
- Contract tests: 12+12 pack balance, distinct documents, challenge coverage, corpus absence,
  exclusion of v4 cases, phase ordering, exactly 24 retrieval calls, label-blind raw schema, hashes,
  byte idempotence, and source privacy.
- Artifact tests: all HIC-R8 counts, fixed seven-policy grid, deterministic winner/null result, and
  tamper rejection.
- Repository QA: targeted Ruff/format, MyPy, compile, focused tests, full test suite, installed CLI,
  repeated `--check`, and `git diff --check`.

## Technical decisions and trade-offs

- Ordered alignment is chosen over bag-of-token coverage because `R32` and `R34` share most tokens
  but make incompatible model claims.
- Bilateral residual is chosen over penalizing every extra query word because marketplace text often
  contains legitimate context that is absent from the casting name.
- Public-corpus IDF replaces hand-written per-model importance. This stays explainable and prevents
  case-specific exceptions, but it may still misweight rare generic descriptors.
- No neural cross-encoder is added. The 10x advantage is full offline reproducibility and auditable
  reason codes; the cost is lower semantic flexibility.
- The most likely failure is that a correct shorthand leaves meaningful unmatched atoms on both
  sides and is falsely rejected, or that a wrong candidate finds a high compact alignment and hides
  a nonnumeric model substitution. The frozen positive and negative gates test both failure modes.

## Confirmation checkpoint

Implementation tasks are not approved until the owner confirms this design.
