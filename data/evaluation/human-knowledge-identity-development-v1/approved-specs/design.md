# Identity-Bounded Human Knowledge Retrieval — Design

Date: 2026-09-13. Mode: Lite. Status: proposed, not implemented or output-tested.

## Overview and evidence

V3's frozen development report shows all 21 settings failing generic negatives and both p95 budgets.
At the highest floor, generic-00 returns five documents through `box`, `collector`, `blue`, with
no character ranks. `HumanKnowledgeRetriever._retrieve_v3` admits any broad searchable-text token;
the character floor cannot close that separate path. `CharacterIdentityIndex.rank` gathers gram-
sharing document IDs but then compares all query windows against all forms of those documents.
Sparse frequencies and document maps are also rebuilt by corpus scans each query.

The measured p95 is 29.37–36.60 ms over 142 documents and 337.15–377.28 ms over synthetic 3,000.
The latter has 419,820 posting entries. These are diagnostic observations, not proof of an exact
CPU attribution or that a proposed algorithm will pass. No new retrieval/profile run occurs during
this planning step. The new design changes architecture with the same 21-config grid and safety
gates; it is not an expansion of the already viewed v3 search.

## Architecture and module boundaries

```text
query → shared normalization → frozen identity core
          ├─ complete-core token postings → exact identity sparse rank ──┐
          └─ weighted gram postings → form dot sums → max/doc + floor ─┤
                                              work budget: abort all    │
                                            bounded union (≤50 docs) ◄─┘
                                                        ↓
                                  existing hashing dense rank → weighted RRF
                                                        ↓
                                                debug-only Human Top-K
canonical RAG ─────────────────────────── final product/status/confidence (unchanged)
```

Add `human_knowledge_identity.py` and `human_knowledge_identity_selection.py` rather than edit the
v3 source-bound modules (`human_knowledge.py`, `human_knowledge_selection.py`, `identity.py`,
`signals.py`, `retrieval.py`). Reuse their catalog/document/candidate types and hashing provider
without changing bytes, so historical v3 report checks still pass. Service/config/schema/UI changes
wire a separate v4 opt-in; they must not route v4 through a modified v3 loader or falsely report v3.
Do not modify canonical retrievers or governance/data projections.

## Identity policy (fixed proposal, frozen by IBR-T1)

Admission inputs: provisional casting only; family casting plus approved aliases. This deliberately
narrows v3's provisional admission inputs: human-verified labels may be verbose listings and are not
clean identity spans. Existing full text remains available for dense ranking after admission, not
eligibility. Multiple provisional variants of a casting keep their distinct IDs; no type quota.

Apply existing normalization, then remove these exact whole tokens identically from identity and
query forms (`identity-core-policy-v1`):

```text
as blister black blue box boxed cabinet carded car case collectible collector diecast
display estate find from gray green grey hot hotwheels in item light local loose maker
miniature missing model new orange outer package pack piece pictured pickup protective
purple red scale sealed shelf silver small sold storage the toy unopened unknown vehicle
wear wheels white with yellow
```

This global, inspectable listing-noise policy is informed by the viewed development failure; it is
not output-blind and cannot establish unseen safety. It removes whole tokens, not substrings, so
`Boxster` is not removed by `box`. Preserve identity numbers and mixed identifiers; never replace
an unknown token with a catalog name. Duplicate normalized forms are deduplicated; a core with no
remaining token is invalid readiness, not silently skipped. Removing colors/common words can
collapse distinct names: record core collisions and preserve every ID; correctness is still gated
by development/final tests. No manual per-target exemption or after-output policy edits.

Exact admission requires all core tokens of one approved form to appear in the query core. This is
stricter than any-token admission but allows wrappers/order differences. The sparse score uses
precomputed identity token IDF for evidence; incomplete token matches do not get a sparse rank.
Character evidence independently rescues misspelling/spacing. Empty core queries return empty before
either channel. No brand/initial/price/series-label fallback.

## Direct character-scoring model

Retain spaced and compact forms, Unicode bigrams/trigrams and stable ordering. Build document-level
DF for `(mode,gram)` over the restricted cores, with `idf = log((N+1)/(df+1))+1`. Each form has
`weight = count × idf`, L2 norm and normalized weights. A posting stores `(form_id, normalized_weight)`;
the stable form ID maps to document UUID, mode and core token count. Duplicate forms per document
are removed, while different documents sharing a casting remain separate.

Create contiguous query-core token windows of identity-core lengths L−1/L/L+1, with modes spaced/
compact, deduplicated in deterministic order. For a query gram absent from the corpus use
`idf_unknown = log(N+1)+1` in the query norm. It contributes no dot product. This avoids v3's loss
of unknown text from the denominator; character scores now have a new index/version contract.

For each normalized query window, traverse only its known gram postings and accumulate
`dot[form_id] += query_normalized_weight × posting_normalized_weight`. Finish every window before
taking the maximum cosine across matching-mode forms/windows for each document. No document-form
Cartesian loop, approximate shortlist or threshold-dependent early partial result. Sort max scores
by descending score/UUID; apply the selected floor and cap channel Top-25. The brute-force oracle
uses exactly this new policy/formula, not the old raw v3 scores.

## Fixed limits and abstention contract

Proposed engineering ceilings, not fitted parameters:

| Limit | Fixed value | Exceeded behavior |
|---|---:|---|
| Normalized query characters | 512 | Empty Human result, `query_limit` |
| Normalized query tokens before noise removal | 64 | Empty Human result, `query_limit` |
| Unique normalized identity forms per document (including modes) | 32 | Index not ready |
| Unique query forms/windows including modes | 256 | Empty Human result, `window_limit` |
| Weighted gram posting entries visited per query | 1,000,000 | Discard all results, `posting_limit` |
| Source candidates | 25 each | Deterministic Top-25 |
| Dense union | ≤50 | Exact bounded scoring |

Limits do not guarantee the timing budget: the implementation must measure. Count visits even to
repeated postings across different windows. Do not silently stop at a cap and return partial top-K.
Debug counters report query forms/posting visits/scored forms, abstention reason and policy version;
do not log raw query text. Budget/noise abstention is a normal debug empty result, distinct from
dependency/index corruption (503). Canonical output is computed independently and is not forced to
abstain. Positive abstentions are misses with unchanged denominators.

## Development protocol and selection

IBR-T1 freezes `data/evaluation/human-knowledge-identity-development-v1/protocol.json` and manifest
with spec/policy/limits/corpus hashes, old pack hash and old development report hash/use disclosure.
Reuse all unchanged 199 dev cases intentionally: they are development and their outputs have been
viewed. Never load v1 final evidence for selection. Commit protocol before v4 outputs. A comparison
with v3 is an architecture diagnostic on the same leaky dev data, not final improvement accuracy.

Evaluate exactly seven existing floors × three weights; keep hashing dimensions/weights/RRF/K fixed.
Save all candidates, counters, labels accessed after retrieval, raw metrics, rejection reasons and
latency samples to `reports/human-knowledge-identity-development-v1/`. Keep all original quality,
safety, real-cost and scale-cost gates. Tie-break MRR, Recall@1, higher floor, lower weight. No winner
means a new FAIL, no v4 artifact/default activation, no final authoring and no T49.

## Cost workload and anti-abstention checks

Record macOS/CPU/Python and non-isolated-host scope, K=5, three warm-ups, nearest-rank raw p50/p95,
index/document/form/posting counts and every work counter. Measure 199 real dev queries. Report the
original 20 dev scale-query IDs separately for before/after diagnostic comparability.

Keep the exact 3,000 synthetic `Scale vehicle model NNNN`/`Synthetic casting NNNN` documents used
by v3, with the same UUID construction, but index their new cores. Add 100 deterministic cost/
correctness probes: targets 0000–0059 exact casting, 0060–0079 single-edit (`Scale` → `Scxle`),
0080–0099 contextual (`listing ... local pickup`). Together with original 20 dev queries this is
120 scale samples, frozen before output. Exact targets and all contextual targets must reach Top-5;
single-edit targets need ≥17/20. A budget-empty-only fast implementation therefore cannot pass.
This is synthetic diagnostic correctness, not an independent test. Require aggregate scale p95
≤150 ms and real p95 ≤25 ms; retain subgroup samples and original-20 p95 separately.

Index/startup/serialization/HTTP/SQL/network/concurrency are excluded. Report isolated microkernel
oracle timing only as supplemental; full retrieval query timing decides the budget. If limit or
workload changes after viewing output, version/freeze a new protocol and preserve the old FAIL.

## Runtime/API/artifact interfaces

New classes: `IdentityCorePolicy`, `IdentityPostingIndex`, `IdentityRetrievalWork`,
`HumanKnowledgeV4Config`, `HumanKnowledgeIdentityRetriever`. Retriever returns existing typed
`HumanKnowledgeCandidate` plus a query-local work object; never store mutable last-query counters
on a shared service instance. Debug adds optional v4 work/policy metadata; existing candidate rank
fields remain optional and unchanged. Health exposes actual v4/index/artifact version.

New opt-in: `PVR_HUMAN_KNOWLEDGE_IDENTITY_ARTIFACT`; if both old v3 artifact and new v4 artifact are
set, reject readiness. Missing both keeps v2. Frozen v4 artifact schema
`pvr-human-knowledge-identity-retrieval-artifact-v1` requires version/configuration/policy/limits,
protocol/corpus/source checksums and full selection report reference plus every candidate metric
summary. No optional evidence bypass inherited from T2 fixtures. Verify report source boundaries,
arithmetic and qualifying winner before ready; no silent fallback/overwrite. Opt-in is experimental
debug evaluation capability, not authorization for default deployment. Runtime/container packaging
must include the bound report/protocol or fail readiness honestly.

## Errors, security and testing strategy

Malformed/stale inputs, empty cores, duplicate IDs, index-limit violation or nonfinite weights fail
closed before artifact/output replacement. Posting abort discards both token and character partial
results. Sparse/dense/character failure maps to the existing dependency policy. Escape debug UI
text; no new network/model downloads, secrets, private data or persistence. Preserve held exclusions.

Unit tests: normalization/noise whole tokens, full exact core, typo-only admission, unseen-gram norms,
oracle score/rank equality, duplicate forms/collisions, ties, counters and every budget edge. Integration/
API/UI tests: per-query counters, opt-in conflict, missing/stale evidence 503, type isolation and
canonical debug-off equality. Evaluation tests: exact grid, raw recomputation, fixed denominators,
all gates/ties, no-winner preservation, synthetic positive probes, no-v1 reads and historical source
hash checks. Full regressions retain canonical/T47/v1/v3 evidence checks. Final holdout follows the
unchanged HRR 105-case/owner-confirmation/all-gates contract only after qualified freeze/commit.

## Alternatives, trade-offs and most likely failure

Raising the old floor cannot close exact generic admission. Stopwords alone on broad human text
leave other irrelevant tokens, so both field restriction and complete-core exact admission are
required. Neural retrieval remains deferred: this failure is eligibility and comparison work, and
a new model introduces a different dependency/artifact surface without removing either requirement.
Approximate gram shortlists or type quotas risk losing/censoring true targets; direct accumulation
first provides an exact, oracle-verifiable baseline with honest hard-budget abstention.

Trade-offs: narrower casting fields can miss human-label synonyms; complete token admission relies
on char rescue for partial/typo identities; global noise removal can collapse color-distinguished
names; unknown-gram norms can reduce recall; bounded work can abstain on difficult queries. These
are explicit risks to be tested, not reasons to waive gates. At 10×, frequent gram postings can still
grow; direct accumulation removes redundant pair comparisons but does not prove the budget. If v4
fails, retain evidence and decide a new policy/representation separately before output.
