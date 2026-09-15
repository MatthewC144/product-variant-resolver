# VAR-PLAN1 — Release field-evidence review requirements

Date:2026-09-15. Lite. Status:authorized bounded offline planning by owner「幫我進行下一步」after
VAR-PLAN1 was named as the next action. No website collection or release approval is authorized.

## Observable requirements

### RFER-R1 — Cover the exact frozen100 source rows
WHEN the plan is built,THE SYSTEM SHALL require exactly100 unique source records from the frozen2025
pilot and one-to-one membership in the cross-catalog review and final family-adjudication queue; any
missing,extra,duplicate or mismatched row SHALL reject the plan.

### RFER-R2 — Preserve source values and nulls
WHEN a field observation is emitted,THE SYSTEM SHALL copy only the source's raw value and SHALL mark
absent color,wheel,tampo,edition and packaging values`unknown`; variant-note text such as`2nd Color`
or`Zamac` SHALL NOT be converted into an unobserved physical color,wheel or tampo value.

### RFER-R3 — Separate identifiers and authority
WHEN a source record enters the review plan,THE SYSTEM SHALL assign a deterministic observation ID
that differs from the source-record ID,leave variant-equivalence ID and canonical UUID null,and retain
the final family decision only as casting-scoped context rather than release approval.

### RFER-R4 — Keep every release held
WHILE VAR-PLAN1 has no field-level owner decisions,THE SYSTEM SHALL keep all100 release records held,
promotion-ineligible and noncanonical,including records whose casting family was merged or accepted.

### RFER-R5 — Make every field independently reviewable
WHEN a reviewer opens an item,THE SYSTEM SHALL show per-field raw value,state,evidence pointer and
allowed next states for brand,casting,year,series,series position,collector/toy number,variant note,
color,wheel,tampo,edition and packaging; conflicts and unknowns SHALL remain representable without
forcing an equivalence decision.

### RFER-R6 — Propose one bounded whole-family batch
WHEN the first manual batch is proposed,THE SYSTEM SHALL select complete families only,cap it at five
families and fifteen source rows,and cover held/merged/new-family contexts plus materially different
variant-note,series or missing-detail patterns where the frozen data permits.

### RFER-R7 — Publish deterministic auditable outputs
WHEN the local planner runs,THE SYSTEM SHALL publish an exclusive JSON plan and readable Markdown
summary bound to source SHA-256 values;`--check` SHALL reproduce and compare exact bytes without
network,SQL,API calls or canonical writes.

### RFER-R8 — Disclose the next gate
WHEN the plan is reported,THE SYSTEM SHALL state that source access/rights remain historical and
unrevalidated,and that owner field review must precede VAR-PLAN2 collection or VAR-PLAN3 identity/
evaluation work. It SHALL NOT claim100 verified variants or progress toward3,000 approved products.

## Out of scope

No new web request,image/OCR inference,database migration/import,runtime retrieval change,canonical
UUID,field confirmation,variant merge,source-rights determination,or3,000-row expansion.
