# AI eval evidence — Pointwise balanced holdout v1

Date: 2026-10-05. Evaluation: PBHE-G1. Result SHA-256:
`8764f2642208b7cfddf63402fb18f487514af1b38a2d183afbc4da41b72a9566`.

## Rubric and evidence

| Dimension | Frozen criterion | Observed | Verdict |
|---|---|---|---|
| Binding integrity | Approved positive/policy/negative hashes and transitive artifacts match before and after scoring. | All frozen bindings matched. | PASS |
| Exact accepted count | At least 5 exact-release-correct matched positives. | 5/53, exactly the minimum. | PASS |
| Exact accepted precision | At least 90% exact correctness among matched positives. | 5/5, 100%. | PASS |
| Positive false no-match | At most 10% of catalog-present positives classified no-match. | 3/53, 5.66%. | PASS |
| Negative rejection | Frozen no-match aggregate gate remains passed without rescoring. | 11/20 no-match, 0/20 matched; reused only. | PASS |
| Identity transparency | Casting and exact-release performance reported independently. | Both 5/5 precision and 5/53 recall. | PASS |
| Output blindness | No row-level query, label, candidate, confidence or prediction persisted. | Aggregate-only result. | PASS |
| No adaptation/runtime | No model, feature, threshold, truth or runtime change. | All guardrails false; runtime unauthorized. | PASS |

## Portfolio interpretation

The frozen policy is precise when it chooses to match, and it made no false matches on the negative
holdout. That safety comes with very low coverage: 54/73 cases are unresolved, positive exact recall
is 9.43%, and combined end-to-end exact accuracy is 21.92%. This is evidence of a well-governed
high-precision abstaining prototype, not a production-ready resolver.

The 53 positives were previously used to evaluate the underlying ranker, although never to fit or
select Pointwise v2 calibration/thresholds and never previously scored by this policy. The negative
20 were independently frozen before their one policy run. These different prior-use histories are
part of the result's stated scope and prevent an unsupported “fully untouched balanced benchmark”
claim.
