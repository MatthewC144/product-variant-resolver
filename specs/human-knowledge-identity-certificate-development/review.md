# QA review — Human Knowledge identity-certificate set v4

Date: 2026-09-24. Verdict: **implementation PASS; historical eligibility FAIL; holdout NOT RUN; runtime NOT AUTHORIZED**.

## Requirements coverage

| Requirement | Evidence | Result |
|---|---|---|
| HICS-R1 | Calibration manifest binds only committed public corpus/evidence and records `private_local_artifacts_read: false` | PASS |
| HICS-R2 | Nine HIC-v1/HIE-v2/HICG-v3 fixed hashes plus all public historical inputs are verified before scoring | PASS |
| HICS-R3 | 142 documents map to 139 authorities; 460 primary-only claims derive 401 minimal certificates; seven contained identities remain unresolved | PASS |
| HICS-R4 | Certificates preserve authority/member IDs, primary casting, ordered claims, elimination steps, deletion proofs, and checksums | PASS |
| HICS-R5 | Query support is computed once against the complete inventory before candidates and has one candidate-independent checksum | PASS |
| HICS-R6 | Shared-maker/incomplete `Honda Accord`, `BMW M4`, and `Bugatti Divo` regressions remain empty | PASS |
| HICS-R7 | Unique partials such as `55 Chevy` can satisfy a complete certificate while disclosing omitted primary claims | PASS implementation; historical recall still below gate |
| HICS-R8 | Exact, structural, and bounded profiles expose only frozen reason-coded relations with digit/frame conservation | PASS |
| HICS-R9 | Empty/ambiguous/unresolved/conflicting support fails closed without rank or lexical tie-break | PASS |
| HICS-R10 | Context comes from a frozen public lexicon with identity precedence and reason-coded wrapper decisions | PASS |
| HICS-R11 | Singleton authority membership, source-order preservation, ranks 1–5 frame veto, and variant non-resolution are tested | PASS |
| HICS-R12 | Certificate decisions exclude series, color, wheel, tampo, edition, packaging, price, provenance, labels, and private outcomes | PASS |
| HICS-R13 | Exact 223/22/24 public rows were rescored with zero retrieval and all sixteen gates were emitted per profile | FAIL product eligibility: no non-reference profile passes every gate |
| HICS-R14 | The null branch persists `winner: null`, zero survivors, zero retrieval, and only three calibration files | PASS |
| HICS-R15 | Conditional protocol/holdout/collection code is synthetically covered; historical failure correctly prevents real protocol, declarations, pack, and raw rows | NOT RUN / BLOCKED as designed |
| HICS-R16 | Evidence schemas are explainable and the API, Dual RAG, PostgreSQL, canonical, release, variant, and physical-feature boundaries remain unchanged | PASS |

## Four separate verdicts

Implementation integrity passes. Authority grouping, certificate enumeration/minimality, alias
bridges, candidate-independent query support, all-rank membership/conflict decisions, immutable
historical loaders, conditional artifact lifecycle, validators, and the five-phase CLI are
deterministic. Sixty focused tests, 181 related regressions, and all 924 repository tests pass. The
only suite warning is the existing Starlette/AnyIO deprecation warning.

Historical eligibility fails. `certificate-exact`, `certificate-structural`, and
`certificate-bounded` all reach zero output on both absent-identity sets, preserve both known
secondary BNR34 vetoes, and report zero computation/retrieval errors. They nevertheless preserve
only 42, 82, and 137 of 168 required existing positive hits. Exact/structural/bounded also retain
only 6/7/5 of 24 prior required targets, 0/4/5 of 10 anchor positives, and 3/7/7 of 12 HIC positives.
No profile satisfies every predeclared gate.

Holdout eligibility was never reached. The formal result is `historical_calibration_fail` with no
survivors and `winner: null`; HICS-T6–T8 are blocked. No protocol, frozen inventory artifact,
negative declarations, 16+16 pack, raw rows, selection report, or new retrieval call exists.

Runtime authorization is absent. Green implementation tests do not override failed product gates.
No private evaluation or change to API, Dual RAG, PostgreSQL, canonical identity, release
promotion, variant UUID, color, wheel, tampo, edition, or packaging is authorized.

## Reproducibility and findings

The frozen v4 development source SHA-256 is
`cf2e207b97f395d2e4b334875ac17f2efa0500b1e675910e0242e562503b665a`. The certificate inventory
checksum is `dafc709027af513e8bd6db20b80cc1c73e096461a05d13c69699b759f05edec7`. The calibration JSON,
manifest, and Markdown SHA-256 values are respectively
`d9ca782bd47252af0a1047776da3add97a5b40b2709b8a5d44bf4e6ecd78cf96`,
`3bb89724f50f5a1229bf36023b84551fe7ee3cd27f5355f74d4fee1fd582ec95`, and
`621ba4e10981790f1acda13d79aab2374a2a40ba2383a1a499e3ea6c65c5b4fb`.

Targeted Ruff format/check, target-local strict MyPy with imports skipped, compileall, installed CLI,
artifact/hash/absence checks, and `git diff --check` pass. The first full-suite attempt exposed a
local macOS virtual-environment issue: hidden editable `.pth` files made a subprocess miss `src/`.
A gitignored `.venv/sitecustomize.py` restored the src-layout path; the previously failing test and
the complete suite then passed without changing repository product/evaluation behavior.

Repository-wide strict MyPy remains disclosed debt rather than a green gate: it reports 51 existing
errors across 18 files, including missing optional dependency stubs, older development-module type
inference, redundant casts, and pre-existing API/service typing. The target-local v4 check has no
diagnostic. HICS-T9 does not rewrite unrelated modules to conceal this debt.

The measured failure is a recall boundary, not an implementation exception. Selecting bounded as
the closest profile would violate exact gates and turn historical evidence into tuning data. V4 was
predeclared as the final identity-admission attempt, so the correct closure is to preserve the null
result, avoid 32 unnecessary retrieval calls, and hand the roadmap back to the separately specified
No Reranker/RRF, Neural Pointwise, and Listwise comparison.
