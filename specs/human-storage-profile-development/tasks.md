# T49.3 — Bounded tasks

Date:2026-09-14. Lite. DRAFT; no subagents unless explicitlyrequested.

- [x] HSP-PLAN:inspect actualconstructor/guard/mathprotocol constraints; draft requirements/design/
  task/protocol and beginnerguide, scopedQA/AIevidence/decision/narrativelog. _(→R1–R9)_
  This is planningdelivery, not approvedfreeze or fullT49.3completion.

G1*:owner confirms requirements, then design, then tasks/proposedcostprotocol before implementation.
Planning was authorized by「請幫我執行下一步」. Subsequent「確認完成，請繼續執行」after the
requirements explanation confirms requirements only; see [approval ledger](approval.md).
Design and tasks/budgets remain WAIT; no three confirmations or runtime approval are fabricated.

- [ ] HSP-1:freeze confirmedspecs/protocol and declarednewprofilecontract. _(→R1,R2,R5–R9)_
  Files:newapprovedspec snapshot/protocol/manifest/approval in a newdevelopment directory and
  newfreezescript. Acceptance:committedapprovedversions; legacydev/finaloutput exposure disclosed;
  allplannedsourcebindings mandatory before realoutputs; no SQL/retrieval in this task.

- [ ] HSP-2:implement newfile/DB readonlyprofile hydration/integrity gate and compositional app
  factory; unit/mock/APIcontract tests, then freeze actualsources/newartifacts. _(→R1–R5,R7)_
  Owner:mainagent withoutsubagents. Files:newprofile/appmodules and newtests/scripts only.
  Acceptance:142typed/raw/sourcechecks, math/storageprotocolsdistinct, no legacy sourcechanges;
  default unchanged, startup/runtime503latch/no fallback, invalidHTTPcontract unchanged, explicit
  versionedhealthdependency; productionURL/default/credentials excluded. Source/runtimeartifact
  freeze before realdev/costoutput. Privatefake tests are not SQL evidence.

- [ ] HSP-3:after explicitisolatedrun approval, bootstrap a newdisposable DB/readrole and collect
  immutable paired199dev correctness outputs; score parity onlyafterrawpublication. _(→R1–R7,R9)_
  Files:newownedDockerverifier and newreports. Acceptance:file/DB ranks/scores/types/UUIDs/payloads/
  workcounters exactlyequal199/199; fullnondebugcanonicalbodies sameas default; errors/emptycases
  retained, no retries or parameter search; SELECT-only denials and startup/poststart503matrixPASS;
  canonical7tables unchanged; newresourcesonly cleanup, rawsource/image-bound failureevidence.

- [ ] HSP-4:run approvedstartup/revalidation/HTTP/core cost protocol and publish QA/rubric/log.
  _(→R1,R6–R9)_
  Acceptance:5startup samples/profile,3warmups/profile,199pairedHTTP/core rawsamples perprofile,
  fixedceilings checked without reruns, nearest-rankp50/p95, errors/abstentions/environment/stages
  reported; scope142only, no oldfinal/live3k/productionclaims. FullT49.3checked onlywhen HSP1–4PASS;
  T49.4 remains separate runtimepackaging/closure, not silentlycompleted by planning.

## Hard exclusions

No oldv4/config/service/identity/snapshot/persistence/supervisor/final source edits; noexistingvolume/
workingDB reset; no defaultrollout, newcanonicalUUID, sourcecollection, ANN/neural/wheel-tampoidentity
changes. The new DB requestprobe is storageintegrity, not SQLcandidate/vectorretrieval.
