# VAR-PLAN1 — Release field-evidence review design

## Overview and architecture

A standalone offline planner reads three already-frozen artifacts:the normalized100-row pilot,the
100-row cross-catalog review,and the final53-family adjudicated queue. It validates their one-to-one
row relationship before deriving a review-only envelope. It does not import product runtime modules,
open a database or contact Fandom.

```text
normalized100 raw fields ──┐
cross-catalog100 holds ────┼─► strict join/check ─► 100 observation envelopes
final53 family decisions ──┘                         ├─► whole-family first batch≤5/15
                                                    └─► JSON plan + readable Markdown
```

## Data and authority model

Each envelope contains`source_record_id`,`observation_id`,`family_review_id`,source row/revision,
casting-scoped decision context,`variant_equivalence_id:null`,`canonical_uuid:null`,and a
`release_review` object fixed to held/not eligible. Observation identity means “this exact source row
was seen”; it does not mean two rows describe the same physical release.

The field vocabulary is fixed. Present source values use`observed_unverified`; null or absent values
use`unknown`. Future human work may create append-only`confirmed`,`conflicted`or`rejected` evidence,
but this planner creates none. Each field retains a JSON pointer to the frozen normalized row. The
planner copies`variant_note`literally and prohibits parsing it into physical attributes.

## First-batch selection

The deterministic greedy selector operates on whole families and stops at five families/fifteen rows.
It first rewards new coverage across family decision (`hold`,`merge_existing_family`,
`create_new_casting`) and data patterns (`second_color`,`third_color`,`zamac`,`series_divergence`,
`multiple_rows_without_variant_note`,`three_rows`). Remaining ties use information score,row count,
then stable family ID. Selection is a workload proposal,not a favorable answer subset; every one of
the100 rows remains in the full plan.

The review worksheet asks a human to confirm each field only from attributable text evidence,record
conflicts,and state whether two observations are the same release,different releases or unresolved.
Unknown fields never compare equal by default. Whole-family batching prevents reviewing one release
without seeing its same-casting siblings.

## Interfaces and error handling

`scripts/plan_release_field_evidence_review.py --run`creates
`reports/release-field-evidence-review-v1/{plan.json,plan.md}`only when the output directory does not
exist.`--check`recomputes the plan and requires exact bytes. Duplicate JSON keys,wrong versions/counts,
row-set mismatch,changed family details,non-held variants,canonical IDs or input hash drift fail closed.

No timestamps are generated,so output is reproducible. The report records historical source licensing
metadata but explicitly does not revalidate current access or legal permission.

## Testing strategy and trade-offs

Tests cover exact100 membership/null preservation,identity separation,all-held authority,per-field
states,whole-family batch bounds/coverage,exclusive publication,source tamper rejection and exact
artifact check. Full project QA confirms no runtime regression.

A larger random batch would sample more rows but make the first beginner review harder and could split
families. A fixed hand-picked list would be easy to understand but less reproducible. Greedy pattern
coverage creates a small explainable workload,at the cost of not estimating population accuracy.
At3,000 rows,the same JSON envelope may need database-backed pagination,but changing storage before
reviewing the current100 would optimize an unvalidated workflow. The most likely failure is treating
`2nd Color`as the actual color or treating two null wheel values as equality.
