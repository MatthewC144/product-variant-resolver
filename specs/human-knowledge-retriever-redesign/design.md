# Human Knowledge Retriever Redesign — Design

> Mode: Lite / Lean Industrial
>
> Status: Proposed; awaiting project-owner confirmation

## Overview

The v1 holdout showed a precise boundary: the second RAG handles marketplace wrappers and all
governance controls, but 11 lexical-variation queries miss their accepted family. The existing v2
retriever first filters to documents sharing an exact normalized token. Its 192-dimensional
`hashing-v1` score is calculated only after that filter, so character information cannot rescue a
misspelled identity that never enters the eligible set. Generic surviving tokens such as `car`,
`model`, or `vehicle` can instead admit verbose provisional-variant documents that fill Top-5.

The proposed v3 adds one bounded character-identity retrieval channel. It does not replace Dual RAG
or add a neural service. The canonical RAG remains untouched; the Human Knowledge RAG remains a
debug-only suggestion source. Model/configuration selection occurs only on a disclosed development
set, then v3 is frozen before a completely new final holdout is authored.

## Architecture

```text
synthetic development pack (199, dev-only, label-derived)
                         │
                         ▼
                  fixed 21-config grid
                         │
            safety gates + deterministic tie-break
                         │
                         ▼
              frozen v3 configuration artifact
                         │
query ── normalize ──┬── token sparse candidates ─────────┐
                     │                                     │
                     └── identity char TF-IDF postings ────┤ union
                                                           ▼
                                             hashing-v1 dense rank
                                                           │
                                      sparse + dense + char weighted RRF
                                                           │
                                                           ▼
                                              debug-only Human Top-K
                                                           │
            canonical RAG ─────────────────────────────────┤
                         │                                 debug evidence
                         ▼
          matched / ambiguous / no_match + canonical UUID

after v3 code/config freeze → new output-blind holdout v2 → owner labels → one final score
```

The crucial separation is authority: v3 may improve what a reviewer sees, but no v3 candidate is an
input to canonical confidence or the final product identity.

## Character identity index

Each typed document exposes a separate `character_identity_texts` tuple rather than reusing its full
`searchable_text`:

- `review_family`: casting plus approved aliases.
- `provisional_variant`: casting plus human-verified label names.

Every value passes the existing NFKC/casefold/token normalization. The index records both a spaced
form and a compact form with spaces removed. It extracts Unicode character bigrams and trigrams,
computes document frequency/IDF, and stores a posting map from gram to stable knowledge UUID. Query
processing creates contiguous normalized token windows near each identity length; the character
score is the maximum TF-IDF cosine across spaced/compact forms and eligible windows. The compact
form handles `DMC` versus `d m c`; windows prevent seller wrappers from overwhelming the identity
portion of a query.

A document must share a posting gram and meet the selected character score floor to enter through
this channel. Exact-token candidates remain eligible independently. `hashing-v1` dense scoring runs
over their bounded union, not over every document. Weighted RRF uses weight 1.0 for sparse and dense,
the selected weight for character rank, `k=60`, and zero contribution for an absent rank. Final ties
use knowledge UUID. There is no fixed family/variant quota because a quota would promote types by
policy rather than evidence and could conceal merge behavior.

## Development and selection interface

Proposed commands:

```bash
python3 scripts/build_family_retrieval_development.py --freeze
python3 scripts/build_family_retrieval_development.py --check

PYTHONPATH=src python3 -m product_variant_resolver.human_knowledge_selection \
  --development data/evaluation/family-retrieval-development-v1/development.json \
  --output reports/family-retrieval-development-v1/selection.json

python3 scripts/freeze_human_knowledge_v3.py \
  --selection reports/family-retrieval-development-v1/selection.json \
  --output artifacts/human-knowledge-retrieval-v3.json
```

The development pack contains 168 positive cases—four per family—with styles
`single_edit`, `spacing_punctuation`, `abbreviation_numeric`, and `contextual_noise`. Its four merge
and seven hold controls reuse governance identities but use new dev-only wording. Ten unrelated
cases are opaque zero-overlap strings; ten contain generic marketplace words without any resolvable
identity. Because positive targets are transformed from indexed labels, this pack is intentionally
leaky and may select configuration but may never support final quality claims.

The finite grid is seven character floors (`0.25` through `0.55`, step `0.05`) times three character
RRF weights (`0.5`, `1.0`, `1.5`). No other parameter varies. Selection first filters on all safety
and minimum-quality constraints, then maximizes MRR@5, Recall@1, higher floor, and lower weight in
that order. The report stores every configuration, raw numerator/denominator, failure reason, and
winner. If no candidate qualifies, no v3 artifact is created.

## Runtime and API contract

`HumanKnowledgeCandidate` and both Pydantic debug branches gain:

```text
character_rank: int | null
character_score: float | null
```

Sparse/dense fields keep their existing meaning. RRF remains the final Human Knowledge ordering.
Health and `debug.model_versions.human_knowledge` expose `human-knowledge-hybrid-v3`; debug metadata
also includes the selected artifact version/checksum. The UI adds character evidence without
changing the two discriminated identity types or rendering external text as HTML.

Configuration is loaded from the frozen artifact rather than environment-selected arbitrary
floats. A missing, malformed, checksum-stale, corpus-mismatched, development-mismatched, or
unsupported artifact makes Human Knowledge not ready and `/resolve` fails with 503 under the
existing dependency policy. There is no silent fallback that could make health say v3 while running
another configuration.

## Final evaluation lifecycle

After the code and winning artifact are committed, a separate authoring task creates
`family-retrieval-holdout-v2`. Its 105 cases retain v1's coverage shape and gates for comparability,
but every query must be new and must differ from v1, development, indexed, Fandom, and existing
human-label query sources. Query/reference pairs are frozen before the project owner labels them;
no v3 candidates may be viewed during authoring/review. The labeled benchmark is then committed
before its one final scoring run.

V2 PASS requires all quality and safety gates, not merely improvement over v1. A changed final
retriever or threshold after v2 scoring requires another independently authored holdout. The v1
report is never rescored as a v3 model-selection comparison.

## Data models and artifacts

### Development manifest

Records schema/version/status, exact case/style/type counts, source authoring script hash, corpus
and source hashes, `split=dev`, `derived_from_indexed_identity=true`, allowed selection use, and all
prohibited final/canonical/persistence claims.

### Character index metadata

Records index version, normalization version, allowed fields by document type, n-gram sizes,
spaced/compact modes, window rule, document/posting counts, corpus versions/checksums, and stable
ordering policy. The posting structure is built in memory from frozen documents; it is not
persisted to PostgreSQL in this feature.

### Selection artifact

Records schema/artifact/retriever versions, development and corpus hashes, implementation hashes,
the fixed grid, raw result for all 21 candidates, rejection reasons, deterministic winner, local
latency disclosure, and exclusions. It is immutable runtime configuration, not a trained neural
model.

### Final holdout/report

Uses a v2 version of the T48 query/decision/benchmark/report contract. Reports retain per-case
candidate type/ID, sparse/dense/character/RRF rank and score, expected rank, errors, raw counts,
gates, limitations, and AI-eval verdict.

## Error handling

- Invalid development counts, transformations, controls, source hashes, split, or usage boundaries
  fail before output replacement.
- Empty identity text, duplicate UUID/ID, non-allowlisted fields, non-finite scores, invalid ranks,
  or nondeterministic ties fail index construction/tests.
- No qualifying development configuration writes selection FAIL but cannot write/replace a v3
  runtime artifact.
- Stale or mismatched runtime artifacts fail readiness; the service never reports a false version.
- Missing optional source rank is valid and contributes zero; missing final RRF rank is invalid.
- Final v2 query/label/benchmark/output failures use the existing atomic, checksum-bound behavior.
- A valid quality FAIL always writes evidence and never triggers automatic parameter changes.

## Security and privacy notes

No network request, live scrape, account data, or external model occurs in development, selection,
or final evaluation. Indexed character fields are allowlisted human-reviewed identity names only.
Queries remain synthetic, outputs escape UI text, report fields are allowlisted, logs retain counts
and versions rather than raw titles, and all human results remain debug-gated. Synthetic generic
negatives explicitly test that fuzzy matching does not turn ordinary marketplace words into false
identity suggestions.

## Testing strategy

- Development builder: exact 199/168/4/7/20 composition, four styles per family, unique IDs/text,
  deterministic checksum, disclosure, atomic failure, and no v1 query reuse.
- Character unit tests: Unicode normalization, spaced/compact grams, TF-IDF, token windows, posting
  candidate bounds, score floors, stable ties, and empty/short text.
- Fusion tests: token-only, character-only, both-source, missing-rank, deterministic weighted RRF,
  K bounds, and unsupported artifact versions.
- Selection tests: exactly 21 configurations, safety-first rejection, all tie-break levels, no-
  winner behavior, artifact hashes, and no v1 file access.
- API/UI tests: strict optional character fields, v3 versions, default debug omission, type-field
  separation, inert text, readiness failure, and unchanged canonical authority.
- Development evaluation: positive/style Recall@5, MRR/Recall@1, merge/hold/unrelated controls,
  existing 100-variant and 42-family wiring regressions, plus disclosed local latency.
- Scale smoke: deterministic synthetic 3,000-document character index/query run with document/
  posting/sample/runtime/hardware disclosure; no database or production claim.
- Final evaluation: v3 source/artifact freeze precedes v2 authoring, owner approval covers 105 cases,
  labels remain hidden until retrieval, all metrics recompute, and FAIL remains FAIL.
- Closure: full suite/data chain, canonical fixture report, compilation, JavaScript, Compose, scope,
  project log, QA review, and AI-eval.

## Alternatives and trade-offs

Removing the shared-token filter and running current hashing vectors over all documents would be a
smaller code change, but hash collisions and generic character fragments would enter the candidate
set without an interpretable safety floor. A character TF-IDF posting index makes eligibility and
score inspection explicit and scales better toward the later 3,000-row goal.

A neural sentence-transformer could provide stronger semantic recall, but it introduces a model
download/cache, checksum/licensing, startup memory, offline packaging, and new performance surface.
Most observed failures are spelling/spacing identity failures rather than semantic questions, so
the Lite iteration first chooses deterministic character IR. Neural retrieval remains a separate
future decision if no predeclared v3 configuration qualifies.

Hard-reserving family slots in Top-5 would raise family recall mechanically, but it would not prove
better ranking and could suppress valid merge-to-variant evidence. A unified evidence-based pool is
retained. Edit-distance query rewriting was also rejected as the primary design because it must
choose a target vocabulary before retrieval and can silently turn an unknown name into a known one;
character candidate generation instead exposes scored alternatives without changing the query.

## 10x and most-likely-failure review

At roughly 3,000 documents, a full character comparison per query is avoidable; gram postings keep
work proportional to shared features and the scale smoke exposes posting explosion before database
design. The synthetic scale result still cannot choose a PostgreSQL schema or ANN index—that remains
T49 after quality passes.

The most likely failure is safety-threshold conflict: a low character floor recovers misspellings
but also returns plausible candidates for generic or held queries, while a high floor recreates the
v2 recall gap. The safety-first selection rule makes that conflict visible. If none of the 21 fixed
configurations qualifies, the correct Lite outcome is redesign—not expanding the grid after seeing
which threshold almost passed.
