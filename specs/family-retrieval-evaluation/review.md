# Family Retrieval Evaluation — Lite QA Review

> Date: 2026-09-12
>
> Mode: Lite / Lean Industrial
>
> Scope: FRE-R1–FRE-R16
>
> Engineering verification: **PASS**
>
> Precommitted retrieval-quality verdict: **FAIL — T49 is not authorized**

## Verdict summary

T48 passes its implementation, reproducibility, leakage-control, safety, and documentation
requirements: the independently authored 105-case test set was frozen before scoring, labels are
revealed only after retrieval, all per-case results reproduce the aggregates, invalid inputs fail
closed, and the canonical/runtime/PostgreSQL boundaries remain unchanged.

The measured Human Knowledge RAG v2 quality gate nevertheless fails. Eight of nine precommitted
checks pass, but lexical-variation Recall@5 is `31/42 = 0.7381`, below the required `0.75` by one
successful case. Overall Recall@5 (`73/84`), Recall@1 (`58/84`), MRR@5 (`65.0/84`), family
coverage (`42/42`), marketplace-noise retrieval (`42/42`), merge controls (`4/4`), forbidden-family
hits (`0`), and unrelated non-empty results (`0/10`) all pass. The all-gates rule means these
strengths cannot override the lexical failure.

This is the intended honest-failure path, not an incomplete evaluation. The v1 result remains
published, the current retriever remains debug-only, and no same-set tuning is permitted. T49
PostgreSQL/pgvector persistence and the approximately 3,000-row expansion cannot begin under the
confirmed acceptance boundary.

## Requirement coverage

| Requirement | Evidence | Result |
|---|---|---|
| FRE-R1 | Query-pack/benchmark manifests bind the 142-document sources, catalog/projection hashes, normalizer/retriever/dense source hashes, `hashing-v1`/192 dimensions, RRF 60, and K=5 before scoring. | PASS |
| FRE-R2 | Query cases contain author/method/noise/output-view declarations; builder tests reject copied or previously used query text. | PASS |
| FRE-R3 | Validators and manifests reproduce exactly 105 cases with 84 positive, 4 merge, 7 hold, and 10 unrelated cases. | PASS |
| FRE-R4 | Every one of 42 accepted families has one marketplace-noise and one lexical-variation case under one group. | PASS |
| FRE-R5 | Exact/normalized copying and unbroken lexical phrases fail validation; all four one-token families retain misspelled challenges. | PASS |
| FRE-R6 | All 4 merge and 7 hold decisions are represented; all 10 invented unrelated queries retain zero corpus-token overlap. | PASS |
| FRE-R7 | `owner-decisions.json` contains 105 attributable approvals bound to query-pack SHA `26e244c...58733`; partial/stale/duplicate decisions fail tests. | PASS |
| FRE-R8 | Query pack, owner decisions, benchmark, manifest, JSON result, and Markdown result all pass byte-reproducible `--check` paths. | PASS |
| FRE-R9 | Manifest reports test 105/train 0/dev 0; all related queries share family groups and tuning/rewrite/threshold uses are excluded. | PASS |
| FRE-R10 | Guarded-label test proves retrieval precedes `expected` access; input/code checksums are validated before scoring; protected files remain unchanged. | PASS |
| FRE-R11 | JSON contains all 105 ordered Top-5 candidates, typed identities/ranks/scores, expected ranks, forbidden ranks, and explicit errors; aggregates recompute from them. | PASS |
| FRE-R12 | Report applies the original nine gates exactly; only lexical-variation Recall@5 fails. | PASS (evaluation behavior) |
| FRE-R13 | Valid run writes `verdict=FAIL`, lists 11 misses, sets `same_set_tuning_allowed=false`, and retains the v2 retriever unchanged. | PASS |
| FRE-R14 | Versioned JSON/Markdown reports link the AI-eval, hashes, raw counts, gates, limitations, and non-production boundary. | PASS |
| FRE-R15 | Diff from pre-implementation T48 commit `b7f6ac1` changes no canonical catalog/benchmark, calibration/policy, runtime retriever/service, migrations, Compose, or PostgreSQL implementation. Queries are synthetic and report fields are allowlisted. | PASS |
| FRE-R16 | 201/201 tests, complete deterministic source chain, canonical report, T47 behavior, compilation, JavaScript syntax, both Compose configurations, and whitespace/scope checks pass. | PASS |

## Verification evidence

The complete Python suite passed **201/201**. It includes unit, integration, API, UI harness,
evaluation/reporting, frozen-data, negative-input, and deterministic-output tests. The only suite
message is a Starlette TestClient deprecation warning for the AnyIO `BlockingPortal` alias in the
local dependency environment; it is not emitted by T48 code and does not change behavior.

The deterministic chain passed fixture validation; the 100-row Fandom pilot; review, base queue,
priority-one evidence/decisions; five priority-two research and decision batches; the 42-new/4-
merge/7-hold registry; the 42-document runtime projection; query authoring; 105 owner decisions;
benchmark freeze; JSON evaluation; and Markdown generation. Every available `--check` ran without
rewriting its target.

A fresh canonical report retained the 21-case synthetic fixture metrics: Recall@10/25/50 `1.0`,
Top-1 `1.0`, MRR@10 `1.0`, hard-negative accuracy `1.0`, precision `1.0`, false-match rate `0.0`,
and coverage `0.8333`. Local warmed measurements were pipeline p95 `2.3194 ms` and in-process ASGI
HTTP p95 `2.6189 ms`; these are fixture smoke figures on macOS arm64/Python 3.12.13 and do not
measure Docker, TCP, PostgreSQL, concurrency, or production.

Python compilation, `node --check ui/app.js`, default Compose configuration, PostgreSQL-profile
Compose configuration, and `git diff --check` passed. The T48.4 evaluator/report/test files pass
targeted Ruff and isolated strict MyPy. Whole-repository Ruff 0.16.7 reports 143 existing style
findings, and whole-repository strict MyPy reports 817 existing findings including optional
dependency imports and legacy test annotations. They are recorded maintenance debt, not changed or
silently waived by T48; the executable full suite remains green.

## Findings and limitations

### Blocking product finding

`lexical_variation_recall_at_5` fails at `31/42`. All eleven positive misses belong to this style:
ten return other candidates without the expected family, and one returns no candidates. The
current retriever first requires a shared token, so dense feature hashing cannot rescue a
fully disrupted name; generic surviving tokens can also fill K=5 with broad human-variant results.

### Non-blocking QA findings

The first canonical-report inspection command assumed the older flat report path and `jq` could not
open that path. Generation itself succeeded in the current versioned subdirectory; inspecting the
actual emitted path confirmed unchanged canonical metrics. No repository artifact was affected.

The benchmark is synthetic and covers only 42 families. One result changes the lexical percentage
by about 2.38 points, and no live marketplace distribution, release-variant correctness, database
scale, concurrency, or production latency is measured. Once published, v1 is development-known and
cannot be an unseen final holdout for a redesigned retriever.

## Carry-forward decision

T48 closes with engineering verification PASS and retrieval-quality FAIL. The present debug-only
Human Knowledge RAG v2 may remain available for local review evidence, but it must not be promoted
to canonical matching, PostgreSQL persistence, production accuracy claims, or the approximately
3,000-row expansion.

The next work must be a separately specified retriever redesign using development evidence that is
not presented as an unseen v1 result. Candidate approaches include fuzzy/character-level candidate
generation, field-aware ranking, or a genuinely neural representation, but the design must choose
through new development data. Any changed retriever requires a newly authored, owner-approved
`family-retrieval-holdout-v2` for final evaluation. T49 remains blocked until that new gate passes.
