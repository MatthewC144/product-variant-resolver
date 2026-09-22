# QA review — Human Knowledge identity-claim graph v3

Date: 2026-09-22. Verdict: **implementation PASS; historical eligibility FAIL; holdout NOT RUN; runtime NOT AUTHORIZED**.

## Requirements coverage

| Requirement | Evidence | Result |
|---|---|---|
| HICG-R1 | Calibration manifest binds only committed public corpus/evidence; `private_local_artifacts_read` is false | PASS |
| HICG-R2 | HIC-v1 and HIE-v2 source/artifact hashes are verified before graph construction and remain unchanged | PASS |
| HICG-R3 | One canonical claim graph and checksum are built before candidate comparison and reused across ranks | PASS |
| HICG-R4 | Context uses the frozen public lexicon, identity precedence, and deterministic reason codes | PASS |
| HICG-R5 | Numeric/alphanumeric comparisons preserve source token, digit run, frame owner, and relation | PASS |
| HICG-R6 | Only the four frozen structural numeric rules are allowed; unequal digit substitutions remain conflicts | PASS |
| HICG-R7 | Prefix/edit/compact relations come from the committed public grammar and bounded rules | PASS |
| HICG-R8 | Hard-conflict preflight runs before rank rules for ranks 1–5; focused tests cover `R32/R33` versus `BNR34` | PASS implementation; measured conflict-veto policy misses the two historical veto gates |
| HICG-R9 | One reference and four ordered categorical policies are frozen; no result-driven scalar tuning occurs | PASS |
| HICG-R10 | Decisions use query text and candidate casting/approved aliases only; forbidden release/variant fields are excluded | PASS |
| HICG-R11 | Exact 223/22/24 public evidence is rescored with zero retrieval and every declared gate is reported | FAIL product eligibility: no non-reference policy passes all gates |
| HICG-R12 | The null branch persists `winner: null`, zero survivors, zero retrieval, and only three calibration files | PASS |
| HICG-R13 | Conditional 16+16 holdout requires historical success; no protocol or pack was created after failure | NOT RUN / BLOCKED as designed |
| HICG-R14 | Exactly-once collection and holdout gates require an authorized pack; no raw retrieval was executed | NOT RUN / BLOCKED as designed |
| HICG-R15 | Candidate evidence, deterministic validators, byte/hash checks, repeated freeze, and `--check` are covered | PASS |
| HICG-R16 | API, Dual RAG runtime, PostgreSQL, canonical identity, release promotion, and physical features are unchanged | PASS |

## Four separate verdicts

Implementation integrity passes. The public grammar, immutable graph, local-frame comparisons,
candidate evidence, five policies, historical loaders, branch-aware lifecycle, validators, and CLI
are deterministic and covered by tests. Fifty-one focused tests, 196 related regressions, and all
864 repository tests pass. The full suite reports one existing Starlette/AnyIO deprecation warning.

Historical eligibility fails. `reference-anchor` preserves all positives but admits 11/12 v4 and
10/12 HIC absent identities. `claim-conflict-veto` still admits the same negatives and misses both
known secondary BNR34 vetoes. The three stricter structural policies reach 0/12 on both negative
sets and 2/2 conflict vetoes, but preserve only 129–134/168 existing positives, 3–4/10 v4 positives,
8/12 HIC positives, and 3–19/24 prior required targets. No policy satisfies all exact gates.

Holdout eligibility was never reached. The formal result is `historical_calibration_fail` with no
survivors and `winner: null`; HICG-T5–T7 are blocked. No protocol, declarations, 16+16 pack, raw
rows, or selection report exists, and no new retrieval call was made.

Runtime authorization is absent. Passing implementation tests does not override failed product
gates. No private evaluation or change to API, Dual RAG, PostgreSQL, canonical identity, release
promotion, variant UUID, color, wheel, tampo, edition, or packaging is authorized.

## Reproducibility and findings

The frozen v3 development source SHA-256 is
`998f5af0983517d5ead54cf5fddaf46a57056245f92ac6d0c00c3279260ab173`. A repeated freeze returns
`calibration_failed_unchanged`; repeated integrity checks return `valid`,
`historical_calibration_fail`, and `winner: null`. Targeted Ruff format/check, target-local strict
MyPy with imports skipped, compileall, installed CLI checks, artifact hashes, and
`git diff --check` pass.

Repository-wide MyPy is known debt rather than a claimed green gate: it reports 51 existing or
cross-module errors across 18 files, including optional dependency stubs and prior HIC/HIE type
inference. A full dependency-graph check from the v3 target surfaces 18 of those issues in six
imported modules; it reports no new direct v3 diagnostic. This closure does not rewrite frozen
source or unrelated modules after observing the result.

The failure is a measured safety/recall boundary, not an implementation crash. Choosing a
"closest" policy would violate the predeclared gates: the loose policies are unsafe and the strict
policies lose too many legitimate identities. The correct outcome is to preserve the null result,
avoid 32 unnecessary retrievals, and require any new algorithmic attempt to use a new specification,
source namespace, and evidence namespace.
