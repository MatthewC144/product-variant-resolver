# Pointwise balanced holdout evaluation v1 — QA review

Date: 2026-10-05. Mode: Lite / Lean Industrial. Verdict: **PASS — frozen gate; HOLD — runtime**.

## Requirement evidence

| Requirement | Evidence | Result |
|---|---|---|
| PBHE-R1 | All dataset/split/catalog/policy/calibration/model/prior-result hashes match PBHE-G1. | PASS |
| PBHE-R2 | Protocol discloses prior positive ranking use and zero prior v2 policy evaluation. | PASS |
| PBHE-R3 | Exactly 53 positives were scored once; the frozen 20-negative aggregate was not rerun. | PASS |
| PBHE-R4 | Casting and exact-release metrics are separately reported and both have 5 correct accepted rows. | PASS |
| PBHE-R5 | 5 exact correct, 100% exact matched precision, 5.66% false no-match and prior negative PASS meet all frozen gates. | PASS |
| PBHE-R6 | Output recursively rejects row-level IDs, queries, labels, candidates and predictions. | PASS |
| PBHE-R7 | Data/model/features/thresholds/runtime remained unchanged and runtime stays unauthorized. | PASS |

## Result

On 53 catalog-present cases, the policy accepted five and all five were correct at both casting and
exact-release level. Exact matched precision is therefore 100%, while exact match recall is only
9.43%. Forty-five cases (84.91%) were ambiguous and three (5.66%) were incorrectly classified as
no-match. The pre-registered gates pass, but the minimum accepted-count gate is met exactly rather
than with margin.

The frozen negative result remains 11 no-match, 9 ambiguous and 0 matched. Across 73 cases, 54 are
ambiguous (73.97%). There are 19 decisive outcomes: 16 end-to-end correct and three false no-match,
giving 84.21% exact precision among decisive outcomes and 21.92% end-to-end exact accuracy when
abstentions count as unresolved. Balanced identity recall is 32.22%.

## Verification

The aggregate result SHA-256 is
`8764f2642208b7cfddf63402fb18f487514af1b38a2d183afbc4da41b72a9566`. Focused tests lock this hash,
all transitive bindings, arithmetic, gates, casting/exact separation, negative non-rerun, recursive
privacy and one-run refusal. Scoped Ruff, strict MyPy, compile, artifact `--check` and diff checks
pass. The existing transformer `torch_dtype` deprecation warning does not affect the result.

## QA decision

The experiment passes its pre-registered evidence gate but does not justify runtime activation. Its
high accepted precision is useful, yet 73.97% combined abstention and 9.43% positive exact recall are
too restrictive for a useful default resolver. The holdouts must not be reused for threshold or
model tuning. Any coverage-improvement cycle requires new development data and a later fresh test;
runtime remains held.
