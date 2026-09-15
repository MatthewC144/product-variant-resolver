# VAR-REVIEW1-PREP — Batch01 owner-review packet requirements

Date:2026-09-15. Lite. Status:authorized preparation by owner「幫我進行下一步」after VAR-PLAN1.
This task prepares evidence/questions;only the owner can create field or equivalence decisions.

## Observable requirements

### VBR-R1 — Bind the exact proposed batch
WHEN the packet is prepared,THE SYSTEM SHALL use exactly the four complete families/11 records selected
by the frozen VAR-PLAN1 artifact and bind its SHA;extra,missing,reordered or duplicated records SHALL fail.

### VBR-R2 — Show raw row differences without inference
WHEN a record is displayed,THE SYSTEM SHALL show source row,toy/collector number,year,series/position,
variant note and source markers exactly as frozen,and SHALL show color,wheel,tampo,edition and packaging
as unknown unless a separate attributable text claim explicitly supports a candidate field.

### VBR-R3 — Separate family evidence from release evidence
WHEN prior research is included,THE SYSTEM SHALL label its approved scope as casting-family context;
a family merge/create decision SHALL NOT populate a release field or approve row equivalence.

### VBR-R4 — Preserve attributable candidate claims
WHEN frozen secondary research names a particular toy number/tool/edition,THE SYSTEM SHALL retain the
claim,publisher,URL and source artifact as`candidate_pending_owner_review`;it SHALL NOT derive additional
claims from URL text,series names,image filenames or family-level matches.

### VBR-R5 — Collect explicit owner decisions
WHEN the decision template is generated,THE SYSTEM SHALL require reviewer,time,reason and evidence refs
for every accepted/rejected field claim,and one of`same_release`,`different_release`,`unresolved`for each
within-family row pair. Initial values SHALL all be null/pending.

### VBR-R6 — Remain fail-closed and noncanonical
WHILE owner confirmation is absent,THE SYSTEM SHALL keep all11 records held,promotion-ineligible,
variant-equivalence null and canonical UUID null;unknown/conflicted evidence SHALL never be forced equal.

### VBR-R7 — Publish deterministic auditable artifacts
WHEN preparation runs,THE SYSTEM SHALL exclusively publish packet JSON,owner-readable Markdown and
decision-template JSON with input/output hashes;`--check`SHALL reproduce exact bytes with no network,
SQL,runtime or canonical write.

### VBR-R8 — Stop at the owner gate
WHEN QA passes,THE SYSTEM SHALL update evidence/AI rubric/log and request owner review rather than
marking the batch reviewed or advancing to VAR-PLAN2/3.

## Out of scope

No new web access,current-rights determination,image/OCR,field truth,owner decision,variant grouping,
database/runtime change,canonical promotion or accuracy claim.
