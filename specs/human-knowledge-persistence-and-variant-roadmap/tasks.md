# T49 — Tasks and approval boundary

Date:2026-09-14. Lite. T49.1 local/T49.2 isolated SQL executed under scoped owner consent; later tasks DRAFT.
No subagents unless owner explicitly requests them. All deliverables within `Product Variant Resolver`.

## Planning delivered now

- [x] T49-SPEC: inspect actual source/model/identity gaps, verify upstream closure without retrieval,
  draft requirements/design/tasks and source-scope/decision/narrative-log evidence. _(→R1,R7,R10–R14)_

Broader G1*: sequential requirements/design/tasks confirmations remain unrecorded. After the detailed
draft explanation, owner「請幫我執行」is scoped to the first local-only task only. It is not a full
schema/DB/profile/source-collection approval. See `docs/evidence/t49-1-execution-scope.md` for the
historical draft commit/hashes and explicit narrow execution exception; no separate approvals invented.

## Implementation tasks

- [x] T49.1: build a local-only142-doc snapshot import-plan/checker and exclusive report CLI; reject
  stale/mixed/partial/duplicate/held IDs before any write. _(→R1–R3,R14)_
  Files:new `human_knowledge_snapshot.py`, `plan_human_knowledge_snapshot.py`, unit tests/evidence.
  Acceptance:100provisional+42family exact ID/type/payload roundtrip; no SQL/network/canonical changes;
  repeat/invalid plan cannot overwrite reports; source checksums/counts visible. First approved task only.
  Evidence:`reports/human-knowledge-snapshot-v1/{plan.json,report.md}`;37focused/448full tests PASS.
  This is exclusive local report publication, not crash-atomic database import or removal of source exclusions.

- [x] T49.2: add separately versioned human snapshot tables/repository and isolated migration/import
  tests after explicit test-DB environment selection. _(→R2–R4)_
  Files:new additive migration, new repository/test verifier. Do not modifycanonical0001/history.
  Acceptance:atomic complete142snapshot; rollback on failure, repeat no-op, collision rejection;
  canonical before/after counts/UUIDs unchanged; no existing DB/volume reset or production URL default.
  Owner「執行測試」after `docs/T49-2-ISOLATED-TEST-PLAN.md` approves its disposable environment only.
  Evidence:`reports/human-knowledge-postgres-t49-2.json`:realSQL PASS,142roundtrip,71doc SQLfault full
  rollback, concurrentfirstimport oneinsert/onenoop, repeatedrows/timestamp identical, canonical7tables
  unchanged;25new/473full tests PASS. Newcontainers/network cleaned; no current persistent testDB.

- [x] T49.3-PLAN:draft optionalfile/DBstorage profile, fullrequestreadonlyintegrity/503latch,
  dev199parity/cost protocol and specs/guide/log. _(→R1,R5–R6,R14)_
  Evidence:`specs/human-storage-profile-development/` and `docs/evidence/t49-3-planning.md`.
  Planningonly:ownerG1WAIT; noapprovedfreeze/newprofilecode/SQL/costoutput. FullT49.3 remainsunchecked.

- [x] T49.3-FREEZE: scoped three-confirmation G1 and HSP-1 approved input freeze. _(→R1,R5–R6,R14)_
  Evidence:`docs/evidence/t49-3-input-freeze.md`;8files/26input hashes,16new/489full tests PASS.
  No adapter/SQL/cost results; pending runtime-source/image binding before real outputs.

- [x] T49.3-ADAPTER: HSP-2 strict file/DBprofile, complete integrity gate, compositional API,
  private mock/API tests and committed42-source freeze. _(→R1,R5–R6,R14)_
  Evidence:`docs/evidence/t49-3-storage-adapter.md`;55focused/544full PASS. Original default and
  scored sources unchanged. Runtime IDs/profile, actual SQL/199 parity/costs remain absent.

- [ ] T49.3: freeze new optional storage-profile/runtime/cost protocol; implement and measure only
  approved adapter strategy without altering scored v4/v3 sources in place. _(→R1,R5–R6)_
  Acceptance:profile/source/config versions frozen before output; file/DB typed parity, eligibility/
  fusion/budget evidence, failure503, default unchanged, raw samples/errors and scope disclosed.
  No old final105 live replay or ANN/neural/global-vector shortlist; no implicit DB feature rollout.

- [ ] T49.4: verify storage gates/full tests/runtime packaging and publish QA/AI evidence/log. _(→R1–R6,R14)_
  Acceptance:exact142roundtrip, transaction/no-canonical-mutation/idempotence/readiness/source tests
  PASS; complete new development/cost evidence without old-final tuning; continued debug-only authority.

- [ ] VAR-PLAN1: build an offline100-source-row field-evidence review plan preserving nulls and
  all release-held statuses, with a bounded first review batch proposal. _(→R7–R10)_
  Acceptance:zero inferred color/wheel/tampo values or canonical IDs; provenance and per-field
  unknown/conflict statuses; source/observation IDs distinct from reviewed variant equivalence.

- [ ] VAR-PLAN2: obtain source-specific access/rights and page/revision/budget approval before
  collecting any extra text or staging500/1,500/about3,000unique real source rows. _(→R11–R12)_
  Acceptance:current permissions/endpoint evidence, no bypass/images, serial cached bounded reads,
  batch parser/checksum/dedup/held/variant/canonical counters; quota never substitutes for review.

- [ ] VAR-PLAN3: obtain explicit reviewed field/lineage decisions for bounded release batches,
  then propose a new identity/public contract and output-blind variant evaluation protocol. _(→R8–R10,R13)_
  Acceptance:same-casting distinguishable variants and unknowns remain separate; immutable legacy
  UUIDs; independent approved variant labels/gates/splits before outputs. No promotion by family consent.

## Dependencies and non-goals

T49.1→T49.2→T49.3→T49.4 for optional storage; separate offline VAR-PLAN1 then source-gated
VAR-PLAN2 and explicitly reviewed VAR-PLAN3. Dataset count expansion does not depend on claiming
all releases verified; approved canonical rollout remains another separately specified feature.
No task automatically enablesv4 default, writes production tables, mints canonical IDs or certifies
variant accuracy. One bounded task per approved handoff. T49.3 protocol/profile draft nowdelivered;
scoped T49.3 requirements/design/tasks-budgets confirmations now recorded and HSP-1 inputfreeze PASS.
Next HSP-2 implements only new adapter/app modules. New SQL-run approval remains separate.
No default rollout; this does not retroactively fabricate broader historical T49 approvals.
