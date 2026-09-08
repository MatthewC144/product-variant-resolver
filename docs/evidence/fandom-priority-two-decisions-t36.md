# T36 Evidence — Priority-2 Batch-01 Owner Decisions

## Claim boundary

T36 records the project owner's explicit follow-up approval of the ten T35 recommendations. Nine
families receive `create_new_casting`; `'55 Chevy` receives `hold`. These are casting-family-only
review decisions. No canonical UUID, verified release variant, PostgreSQL row, runtime candidate,
calibration input, or evaluation label is created.

## Result

The derived queue preserves the four T34 exact-family merges and adds ten completed priority-2
decisions. Its cumulative state is:

- 14 completed family decisions;
- 39 pending family decisions;
- 4 accepted existing-family merges;
- 9 accepted new review-layer casting families;
- 1 held family decision;
- 28 held Wiki release variants;
- 0 promotion-eligible families.

## Validation behavior

`apply_fandom_priority_two_decisions.py` verifies the T34 queue and T35 research checksums, requires
valid reviewer/time/provenance metadata, and requires the decision batch to cover every research
packet exactly once. A decision must match the approved machine recommendation, use
`casting_family_only`, keep `variant_decision=hold`, cite its research packet, and use no existing
target ID. A new-family decision additionally requires the dedicated casting page, independent
source count, two distinct hosts, and absence of an exact catalog candidate.

The script copies the T34 state, preserves its four completed decisions and prior batch metadata,
adds the ten T36 decisions, and emits a new JSON/Markdown/manifest set. The prior queues remain
unchanged.

## Verification

- Focused tests: 6/6 passed after correcting a test-only expected prior batch ID.
- Changed approved outcome: rejected.
- Incomplete decision batch: rejected.
- Deterministic `--check`: passed.
- Result SHA-256:
  `2b82ca5023439857f186aa0ab122f0b4511290bb4d1303ac533df5c96fbc6790`.
- Report SHA-256:
  `fe00de56e8c425fa5f80c06722deb702f4fb357d1e40495efb4548830bcfaff9`.

The final repository-wide suite count and supporting checks are recorded in the QA review and
Project Log after the complete verification run.
