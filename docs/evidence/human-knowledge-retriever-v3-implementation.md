# Human Knowledge Retriever v3 — HRR-T2 Implementation Evidence

> Date: 2026-09-12
>
> Mode: Lite / Lean Industrial
>
> Status: HRR-T2 engineering PASS; v3 configuration selection not started

## Outcome and authority boundary

HRR-T2 implements the mechanics needed to test `human-knowledge-hybrid-v3`, but does not select or
activate a configuration. The normal application still constructs `human-knowledge-hybrid-v2`.
V3 is available only when `PVR_HUMAN_KNOWLEDGE_RETRIEVAL_ARTIFACT` points to a strict, checksum-
bound artifact whose configuration belongs to the 21 options frozen in HRR-T1. No such artifact is
checked into the repository yet.

The new candidate source remains the second, debug-only RAG. Character, sparse, dense, and RRF
evidence cannot set canonical UUID, canonical ID, product, confidence, status, policy, or
calibration. An integration comparison confirms that the same non-debug request produces the same
serialized canonical response under v2 and an ephemeral v3 test configuration.

## Retrieval implementation

`human_knowledge.py` now exposes a separate `character_identity_texts` contract. Review-family
documents contribute only `casting` and approved `aliases`; provisional variants contribute only
`casting` and `human_label_names`. Brand, decision reasons, URLs, source IDs, held releases,
pricing keywords, series/variant labels, raw initial recognition text, and canonical attributes are
not character-index fields.

`CharacterIdentityIndex` normalizes each allowed identity with the existing NFKC/casefold/token
normalizer, stores spaced and compact forms, and builds Unicode bigram/trigram document-frequency,
IDF, and inverted posting structures. Query processing creates contiguous token windows within one
token of known identity lengths. Only documents reached through a shared posting gram are scored;
TF-IDF cosine is computed over that posting-derived set, a score floor controls character admission,
and equal scores use stable knowledge UUID order.

The current 142-document corpus produces these deterministic in-memory metadata values:

| Measure | Value |
|---|---:|
| Documents | 142 |
| Posting keys | 4,508 |
| Posting entries | 19,001 |
| Gram sizes | 2 and 3 |
| Forms | spaced and compact |
| Window radius | 1 token |

The v3 retrieval branch independently ranks at most 25 token candidates and 25 character
candidates, unions their IDs, and computes the existing 192-dimensional `hashing-v1` dense score
only across that bounded union. Weighted RRF adds a contribution only when that source rank exists;
a missing rank is stored as `null` and contributes zero. Final ties again use stable knowledge UUID.
The v2 branch remains separate so its previous token-gated behavior and byte-reproduced evaluation
stay unchanged.

## Artifact, API, and failure contract

`config.py` adds artifact and development-pack paths, but no environment variable for arbitrary
score floats. The loader requires the v3 schema/retriever/index versions, exact field allowlists,
one of the seven frozen score floors, one of the three frozen character weights, fixed sparse/dense
weights, dense dimension 192, RRF `k=60`, selection K=5, and per-source cap 25. It also verifies the
human catalog, family projection, development pack, development manifest, and implementation SHA-
256 references. Missing, malformed, widened, stale, post-output, or corpus-mismatched input prevents
service construction and makes health/resolve return not-ready/503 rather than falling back.

`schemas.py`, `service.py`, and `api.py` add optional `character_rank` and `character_score` to both
discriminated Human Knowledge debug candidate types. Debug metadata publishes the character-index
contract plus selected artifact version/checksum, while health names the active retriever and
artifact. Without debug, none of these fields is serialized. A runtime character-index exception is
converted to `dependency_unavailable`/503 with no identity.

`ui/index.html` and `ui/app.js` add a Character rank/score column and artifact evidence. All values
still pass through `textContent`; no HTML insertion or external dependency was introduced.

## Historical v2 compatibility

The v1 holdout, labels, metrics, thresholds, and report bytes were not edited and were not used to
choose a v3 parameter. Its old reproducibility contract had recorded the SHA-256 of the complete
`human_knowledge.py` file. Adding an opt-in v3 implementation to that file necessarily changes the
live file hash even though the separate default v2 branch is unchanged.

The historical benchmark/evaluator therefore now validates the frozen v2 implementation SHA
`5bf582b921b62945b7e4405beb98822abd876b870bdb5267854764c2e1ab2982` as a historical identity
constant, then requires the current default v2 path to reproduce the existing JSON/Markdown bytes.
This preserves rather than rewrites T48 evidence. It does not make v1 a selection input or a new v3
quality claim.

## Verification

The HRR-T2-related unit, integration, API, UI, and historical evaluation group passes 56 tests. The
complete repository passes **223/223 tests** with one previously known Starlette/AnyIO deprecation
warning. Focused checks also pass:

```text
ruff check --select F,I <HRR-T2 source and test files>
  All checks passed

mypy --follow-imports=skip human_knowledge.py config.py service.py
  Success: no issues found in 3 source files

node --check ui/app.js
  PASS

build_family_retrieval_development.py --check
  verified 199 dev cases; retrieval_executed=false

build_family_retrieval_benchmark.py --check-query-pack / --check
  frozen v1 query pack and benchmark remain reproducible
```

Executable coverage includes field allowlists, Unicode spaced/compact postings, metadata, exact
character score/tie behavior, character-only and sparse-only candidates, missing-rank RRF,
empty/short/invalid inputs, K bounds, strict artifact values and source SHA, stale implementation
rejection, health and debug versions, OpenAPI character fields, UI rendering/XSS safety, runtime
503 behavior, and canonical/debug-off compatibility.

## Limitations and next step

The successful typo fixtures prove the architectural path—for example `Protn Sagx` can reach the
`Proton Saga` review family without a sparse rank—but they are implementation tests, not aggregate
quality evidence. No threshold or weight has been chosen, no development metric has been calculated,
and no 142/3,000-document latency claim has been made. V2 stays active; T49 and PostgreSQL expansion
remain blocked.

HRR-T3 is next. It must run exactly the 21 configurations frozen before this implementation,
publish raw safety/quality/cost outcomes for all candidates, apply the precommitted tie-break, and
either write one checksum-bound winner or publish selection FAIL without broadening the grid.
