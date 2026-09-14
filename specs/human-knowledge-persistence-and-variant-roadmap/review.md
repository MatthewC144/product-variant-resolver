# T49 planning review

Date:2026-09-14. Lite. Specification completeness/internal trace review:PASS for draft delivery.
Historical draft G1* owner approval:WAIT; no three sequential confirmation messages recorded.
Current scoped T49.1 execution consent:「請幫我執行」after full draft explanation; broader G1 remains
WAIT. Local T49.1 G2/G3*:PASS (37focused/448full tests and real142doc plan/checker).
Subsequent T49.2 owner「執行測試」confirms the separately described disposable environment/scope.
T49.2 scoped G2/G3*:PASS:realPostgreSQL142roundtrip,71docfaultfullrollback, concurrentinsert/noop,
repeat identical rows/timestamp, corrupt/partial rejection, canonical7tables unchanged, ownershipcleanup.
25new/473full tests PASS. No production/runtime-profile/per-query-SQL/cost/variant-quality gate passed.

Subsequent scoped T49.3 G1:PASS after three sequential confirmations with exact commit/SHA sources.
HSP-1:PASS,8file inputfreeze/26pins,16new/489full tests, Ruff F/I/isolated strict MyPy PASS;
see `docs/evidence/t49-3-input-freeze.md`. This does not retroactively approve the historical broader
T49 draft. HSP2–4/fullT49.3/T49.4 remain incomplete; new adapter/SQL/cost results and run approval absent.

RequirementsR1–R14 have observable boundaries and tasks; design includes overview/models/interfaces/
error handling/security/testing/alternatives. Existing canonical migration cannot accept unreviewed
human knowledge without violating identity authority, so new independent snapshot tables are proposed.
Existing142 knowledge and100release observations are separate units. All100source colors are null,
and dedicated wheel/tampo fields absent; no facts invented. Legacy source/UUID/final evidence immutable.

Proposed T49.1 is local142doc import-plan validation, notSQL/network writes. Further isolated DB
selection and versioned profile/cost experiments are separately bounded; release-field review,
collection rights/pages/budgets and new variant protocol precede any future canonical promotion.
The approximate3,000-row goal counts real dedupsource releases, notsynthetic/approved-product quota.

Read-only benchmark/final checks PASS; document whitespace/link checks and preserved source hashes
checked at handoff. No new migrations/runtime or model metrics. Source access/terms remain pending;
general API guidance does not grant Fandom permission. Stop at owner requirements confirmation under
spec-dev-loopLite at draft delivery. Historical source evidence remains
`docs/evidence/t49-planning-scope.md`. Subsequent narrowly authorized local T49.1 execution is
documented in `docs/evidence/t49-1-execution-scope.md` and narrative PROJECT-LOG. Subsequently
authorized isolated T49.2 evidence is `docs/evidence/t49-2-human-knowledge-postgres.md` with AIrubric.
T49.3 onward remain unexecuted. HistoricalT04verifier hardcodes0001 despite usinghead; it is not
claimed current0002QA. New dedicated0002verifier covers the additive downgrade/upgrade cycle.
Application importer/reader enforce complete immutable snapshots; privileged direct SQL corruption
is detected, not prevented by triggers. Process-kill cleanup/crashdurability untested; these are
disclosed limitations, not blockers to this bounded temporary SQL correctness task.

T49.3 planningdelivered in `specs/human-storage-profile-development/`:draftreview PASS/G1WAIT;
fullT49.3/HSP1–4 implementation/approvedfreeze/cost NOT RUN. Proposed fullrequestreadonlyintegrity
gate is distinct from SQLcandidate/vector retrieval; HTTPcost includesitsSQL/network work.
Newprotocol references unchangedmathprotocol separately,199dev only, fixedparameters/no finalreplay.
Source/JSON/draftstatus checks and storedupstreamchecks PASS without newprofile/SQL/retrieval output.

## T49.2 requirement coverage

| Requirement | Verification and result |
|---|---|
| R1 preserve source/UUID/final/default | Git byte comparisons + stored plan/final checker PASS; no new final collector |
| R2 separate human authority | Independent2tables/142typed docs; actual canonical7tables fullrow snapshots identical PASS |
| R3 complete pinned snapshot | Preconnection sourceplan rejection, SQLtyped/raw roundtrip, held/partial/duplicate/corrupt rejection PASS |
| R4 atomic/nooverwrite/idempotence | Genuine71doc SQLfault rollback, concurrentinsert/noop, same imported_at, corruptstorage no-repair PASS |
| R14 scoped first deliveries | Local T49.1 then explicit isolated T49.2 consent; future DBprofile/collection/promotions WAIT |
