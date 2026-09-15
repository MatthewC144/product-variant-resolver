# VAR-REVIEW1-PREP — Batch01 owner-review packet design

## Overview and architecture

The offline preparer reads the exact VAR-PLAN1 plan plus three existing research packets:priority-1
family evidence,priority-2 batch01 research,and priority-2 batch04 research. The plan determines the
four families/11 rows;research can annotate only claims it already contains. No remote page is opened.

```text
VAR-PLAN1 selected IDs ────────────┐
normalized raw row envelopes ─────┼─► strict packet join ─► packet.json
frozen family/research evidence ──┘                       ├─► owner-review.md
                                                         └─► decisions.template.json
```

## Evidence levels

`source_observation`means a value appears in the frozen2025 list but has not been owner-confirmed as
release truth.`family_context`means earlier owner decisions established only casting/tool lineage.
`candidate_pending_owner_review`is an attributable secondary text claim that may support a particular
field/row after review. URL slugs are never parsed as facts.

For batch01,the packet may surface three specific secondary links already written in research:
Lamborghini HYW93 is named as a2025 release;Audi JBC35 is described as a2025 Super Treasure Hunt;
Nissan HYX54 is mapped to the Tooned tool. Subaru's existing evidence is family-level because the human
Zamac variant was not safely mapped to one frozen2025 row. All physical colors,wheels and tampo remain
unknown,including Nissan's URL slug.

## Decision contract

Each row has a pending field-decision slot for only candidate secondary claims;source-observed fields
remain visible but still require exact accept/reject/unknown actions if the owner chooses to validate
them. Each within-family pair receives a pending relationship with allowed values`same_release`,
`different_release`,`unresolved`. A completed event must bind packet SHA,reviewer,time,reason and evidence
references. This preparation writes only a template and zero decisions.

## Interface,error handling and testing

`scripts/prepare_release_field_review_batch.py --run`publishes only into a nonexistent
`reports/release-field-review-batch-01/`directory.`--check`rebuilds all three files. It rejects a changed
plan SHA,record/family mismatch,missing research packet,scope other than casting-family-only,non-held
row,duplicate pair or prefilled decision.

Tests verify4/11 exact membership,raw/null preservation,family-vs-row claim separation,the three allowed
row-specific claims,all three+three+three+one=10 unique within-family pairs,all-null decision template,
exclusive/drift/tamper behavior and no network/database clients. Full QA checks runtime regressions.

The packet intentionally repeats enough context for a beginner reviewer. At10×,a UI/database may replace
Markdown,but the review contract should remain. The largest risk is treating a convenient series name,
URL slug or family-level Zamac phrase as row-specific physical truth.

## Owner decision event01

The owner answered`繼續下一步`immediately after the explicit Lamborghini conservative-decision question.
Record that response as authorization for Lamborghini only. A generic read-only validator checks the
event against packet SHA,required candidate/physical fields,all family pairs,grounded values,evidence,
reasons and summary. It performs no publication or mutation. Other families remain outside the event.

Decision02 extends the same validator with explicit additional source-observation fields. The owner
answered`是`to the Subaru conservative proposal,so HYY12's literal variant note is required and confirmed
while its physical color remains unknown. This extension accepts no arbitrary field:the field must exist
in the same packet row,and a confirmed value must equal the frozen raw value.
