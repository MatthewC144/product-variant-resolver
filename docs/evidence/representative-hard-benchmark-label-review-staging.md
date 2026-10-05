# RHB-T6 label-review staging evidence

Date: 2026-10-05
Mode: Lite / Lean Industrial
Verdict: **PASS — 60 PROPOSALS STAGED LOCALLY; ZERO LABELS APPROVED**

## What was authorized and built

The project owner authorized a local-only review workspace for the exact query pack SHA
`97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a`, governance overlay content
SHA `7f3a87ea250f38245ba4ba376290c370f0ccc9d96fffadc9bf7f8c479da67cbe`, and CAR authority SHA
`72c11aeb8db03267a8deca4f50eb09d89c2c423a7e9ca983f498f76e80553117`.

The exact response is stored in the existing Git-ignored private directory as a `0600` ledger. The
builder creates a `0700` review directory containing:

- `evidence-packets.json`: 60 query-bound packets with exact catalog surface evidence and admitted
  authority metadata;
- `staged-label-proposals.json`: 60 non-approved proposals requiring later owner decisions.

The tracked `rhb-t6-label-review-manifest-v1.json` contains only hashes and aggregates. It publishes
no query, source-row reference, UUID proposal, owner text or row-level label data.

## Evidence method and why it is conservative

The staging builder is not the resolver. It performs no sparse/vector retrieval, RRF, reranking,
confidence policy, Pointwise/Listwise inference or evaluation. It checks exact normalized
casting/alias surfaces and alphanumeric toy identifiers against the complete frozen catalog. Any
candidates are sorted by canonical UUID, not relevance.

A staged `matched` suggestion requires one and only one allowlisted CAR authority record with both an
exact toy identifier and casting/alias surface in the query. Catalog surface evidence without a
unique admitted authority suggests `ambiguous`. An explicit out-of-scope brand with no catalog
candidate may suggest catalog-relative `no_match`. Everything else remains held. Provisional
challenge tags are copied only as pending questions; none is verified automatically.

Historical human labels, `data/human_labeled_names.json`, historical failure categories, resolver
output and Development/Test split are not read. No failure type or hard-negative flag is proposed.

## Staging result and discovered data gap

| Suggested owner outcome | Count | Meaning before review |
|---|---:|---|
| `matched` | 0 | No query has unique admitted identifier-plus-casting evidence. |
| `ambiguous` | 5 | Catalog surface evidence exists but cannot identify one admitted UUID. |
| `no_match` | 4 | Explicit foreign-brand query with zero frozen-catalog candidates. |
| `held` | 51 | Evidence is insufficient for an automated suggestion. |

The most important finding is the distinction between **permission capacity** and **data overlap**.
The governance overlay legally permits up to 20 matched labels, but it cannot create query evidence.
Only one private query surfaces an admitted family, and it corresponds to three approved releases
with different toy identifiers, none present in the query. It is therefore staged as
ambiguous, not matched.

The current 60-query pack cannot satisfy the intended 20 matched cases without new owner evidence or
a separately governed query-pack/source revision. The staging system does not hide this shortfall or
convert held rows to meet 20/20/20.

## Hashes and boundary

| Artifact | SHA-256 |
|---|---|
| Private authorization | `37e2a4874f1c8423da8a4903b36ebdfc53598353f9119f1aee5b935d2affd250` |
| Private evidence packet content | `a2e8f2f84b88fe23b9746426ea366f626b36f03bd1cab0cce323ce3e484e85f6` |
| Private staged-proposal content | `6c495624e5a623ff769afe1e17adbbf387b78cd6c49b2010c4ff820d878a985d` |
| Public aggregate manifest | `457f3c9a986b4d18a4cff0dfb494868279b7f32a27e0093ce1d4f86fdd22bb10` |

Every proposal remains `staged_pending_owner_review`, `owner_decision_recorded=false`, and
`score_eligible=false`. No `labels.json`, held-label artifact, split, benchmark manifest, raw resolver
result or scored result exists. RHB-T7 and resolver evaluation remain unauthorized.

## Verification

- Builder returns `created` and then `unchanged`; all private files are `0600` under a `0700`
  workspace, while the aggregate manifest is `0644`.
- Ten focused tests cover deterministic counts, canonical replay, Subaru ambiguity, public privacy,
  authorization tamper, partial-output safety, overlay lifecycle replay, forbidden artifact absence
  and dependency boundaries.
- All 139 representative-benchmark tests pass. Ruff, formatting, strict MyPy, compile, Git-ignore,
  canonical JSON and diff checks pass.

Next allowed action: present staged proposals to the project owner in review batches. A proposal may
become a label only after an explicit row/batch decision.
