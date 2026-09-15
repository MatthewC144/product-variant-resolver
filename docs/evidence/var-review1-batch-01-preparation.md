# VAR-REVIEW1-PREP — Batch01 owner-review packet evidence

Date:2026-09-15. Lite mode,main agent,no subagents. Verdict:packet preparation PASS;owner decisions0.

## Result

The preparer binds VAR-PLAN1 plan SHA`f470d731…675a`,the normalized100-row source and three frozen
research artifacts. It selects exactly the four approved whole families/11 rows and creates10 unique
within-family pairs. Every row remains held with null canonical UUID and variant equivalence. The
decision template has143 field slots(11×13)and10 relationship slots;all are null/pending,with reviewer,
time,reason and evidence empty.

The owner-readable packet shows exact source row,toy/collector number,2025 year,series/position,variant
note and markers. Color,wheel,tampo,edition and packaging stay unknown. Prior family create/merge/hold
decisions are copied as casting-only context and explicitly have no release effect.

## Three bounded candidate claims

Only existing frozen observed text that names a particular toy number is exposed as
`candidate_pending_owner_review`:

- HYW93:Lamborghini Huracán Sterrato and its2025 release are named by Hot Wheels Collectors News.
- JBC35:HW Treasure describes a2025 Super Treasure Hunt using the'87 Audi quattro casting;`edition`
  is a candidate field,not yet confirmed.
- HYX54:Diecast Radar maps the2025 HW J-Imports row to the Tooned Nissan tool. Its URL contains a color
  phrase,but the frozen observed claim does not;the packet explicitly prohibits accepting color from
  the URL slug.

Subaru BRZ has family-level Zamac evidence but no safe mapping from that human record to one of the
three2025 source rows,so no row-specific candidate is created. This prevents a plausible word match
from becoming release truth.

## Frozen artifacts and QA

Packet/Markdown/template/manifest SHAs are`2e2adee3…00b2`,`08bd164a…8e69`,`bc01138a…3724`,and
`6957176f…5c63`. The manifest records network requests0,owner decisions0,canonical changes0 and all
rows held. Exact regeneration is available with:

```bash
.venv/bin/python scripts/prepare_release_field_review_batch.py --check
```

Eleven focused tests cover4/11 membership,raw/null fields,family scope,three exact candidate claims,
10 unique pairs,all-pending template,manifest hashes,exclusive/drift/changed-plan rejection and absence
of network/database clients. Full suite579/579,Ruff F/I,strict MyPy and compileall PASS;one existing
Starlette/AnyIO warning remains.

No remote page was opened and current rights were not revalidated. This is an evidence presentation,
not human verification,source clearance,release grouping,canonical promotion or variant accuracy.
