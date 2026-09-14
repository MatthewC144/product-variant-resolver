# T49.3 — Storage profile design

Date:2026-09-14. Lite. DRAFT; no implementation or approved protocol yet.

## Overview and architecture

Propose `human-storage-hydration-development-v1`, two explicit modes: `file_snapshot_reference`
and `postgres_snapshot_experiment`. Original `product_variant_resolver.api:app` remains unchanged.
Only a new experimental app factory selects the profile, with canonical backend fixed offline and
legacy v3/v4 environment switches rejected as conflicting experiment inputs.

```text
fixed file plan OR selected PostgreSQL snapshot
  → full pinned-source/typed/raw verification → cached142doc catalog/index
each valid request → read-only full-snapshot integrity gate → unchanged human-v4 math → debug only
                                                    └── unchanged canonical resolver → final answer
```

The cache contains a verified immutable snapshot, not permission to ignore a broken configured DB.
Each /health and /resolve revalidates it. SQL fetches the selected142docs/header for integrity,
not candidates or vector TopK. Therefore HTTP has per-request SQL/network costs even though human
retrieval calculations stay in memory. Index builds happen at startup, not everyrequest.

## Data models and versioning

Reuse T49.2 hk_snapshot/hk_document and original complete142doc plan, without changing its module,
schema/pins/counts/guards. DB names stay `pvr_t49_2_<12hex>` to satisfy the existing disposable reader
guard; fresh container/network names and ownership identify the new T49.3experiment separately.
No newmigration/hk_embedding/release tables. Runtime adapter only reads; testbootstrap alone writes.

New strict storage artifact records profile/protocol version+hash, selectedsnapshot ID/content,
baselineinput hashes, sourcebinding manifest hash, unchanged math parameter/protocol reference and
explicit mode. Credentials/actualDB URL are external temporary environment values, never artifact
fields, response/log content or Git. Unknownkeys/missingfields/type changes/stalehashes reject.

The existing HumanKnowledgeV4Config requires the old math protocol SHA31802…; preserve that field
as the **mathematical protocol**, not replace it with a new storage protocol hash. New wrapper
artifact/version/SHA identifies the storage experiment, references bothprotocols and passes unchanged
mathparameters to the unchanged v4 constructor. Do not repurpose the old v4 artifact or claim its
postgresql/default exclusions were relaxed. Source-binding evidence captures all imported modules,
not merely the newfile names; approval/configfreeze precedes realoutputs.

## Interfaces and composition

Proposed NEW files, not implemented now:

- `human_knowledge_storage_profile.py`:strict profile loader, verifiedfile/DB hydration, cached
  typedcatalog, readonlyintegrity probe and provenance descriptor.
- `human_knowledge_storage_app.py`:explicit experimental factory wrapping existing
  `api.create_app(settings, service_factory=...)`; construct existing ResolverService with verified
  HumanKnowledgeCatalog and unchanged math config via its constructor. No monkeypatching oldglobal
  app/route/source; no modifyingconfig/service/strict response models.
- New freeze/verifier/report scripts:bind newprotocol/source/runtime inputs, own newisolated DB,
  run fixeddev comparison/cost/failuretests and publish exclusively. Do not change T49.2supervisor.

Propose a NEW ResolverService adapter subclass:its resolve method probes the snapshot, delegates
to unchanged super.resolve, and adds only a debugtiming key `human_storage_integrity`. ExistingAPI
validates the request/debugenabled setting before calling thisadapter, preserving400/415/422 and
not probing invalidresolve requests. Newhealth-only wrapper probes/augments health; sharedfailure
latch makes app.state.service unavailable on failure. No oldroute/global/service source monkeypatch.
The implementation must demonstrate invalid400/415/422 stayinvalid, not accept or mutate them.
/health may add a versioned `human_knowledge_storage` DependencyHealth entry through the new
wrapper; the original `database` dependency still means canonicalbackend, not misleading humanSQL
health. /resolve nondebug body/schema staysidentical; debug exposes newartifactversion/SHA through
existingfields. Secrets absent, no middleware rewriting canonicalvalues or schema expansion.

## Error handling and lifetime

Start invalid→notready app with503, not fallbackdefault service. Runtimefullprobe mismatch/SQL
outage→latch notready; /health503 and valid/resolve503 untilrestart. Do not autoheal corruption,
silently usecache/file/latestsnapshot or retry requests. No assertion that unchangeddefault app now
depends on DB. This availability trade-off is intentional and must be measured/approved.

## Security and isolated execution

New disposable internalnetwork/tmpfsDB/nohostports/exactownershipcleanup as a separately approved
future run. Existing T49.2permission did not automatically authorize this later DB run. Bootstrap
owner installsunchanged migrations and fixturebaseline/snapshot, creates a dedicated LOGIN role
with NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOINHERIT, CONNECT/schemaUSAGE and SELECT onlyon2human
tables. Newapplication credentials use thatrole; assertINSERT/UPDATE/DELETE/TRUNCATE denied.
Bootstrap role alone performs controlledfaultfixtures; assertcanonical7tables fullrows unchanged.
Copy required sources byte-exactly with readable copy modes, never change original600files/oldimages.
Roles/passwords/tmpfsdata disappear with this new testDB; no productionrole/durability claim.

## Testing and cost strategy

Freeze199dev IDs/queries from pinneddevelopment pack, not final data. Compare newfile vsnewDB
rankings/types/UUIDs/rawpayloads/scorecomponents/workcounters, and both nondebug canonicalbodies
against unchangeddefault using identical requestIDheaders. Exclude only debug timing/version label
fields where explicitlyexpected; do not normalize semantic mismatches away. Schema500char HTTP
limit stays500; directcore limits512chars/64pretokens/forms256/postings1M remain unchanged.

Raw correctness outputs published before score; failurematrix separatelycovers startupmissing/
invalidprofile, badhash/namespace/source/mixed/partial/unavailableDB and afterstartdisconnection/
controlledcorruption/partialchildren, plus latch, nofallback, SELECT-onlypermission and invalidHTTP.
No automatic retries. Existingv4 has already selected0.5/1.0; no parameter or profilewinner search.

Measure5fresh profile-factory startup samples in separate Pythonprocesses perprofile; timing excludes
Pythonimports/processlaunch/Docker/DBbootstrap and is profileinitialization, not fullcoldboot.
Then one separate singleworkerUvicorn server perprofile handles pairedrealHTTPloopback requests
sequentially(concurrency1). Core runs in oneverifierprocess with prebuiltverifiedprofileindexes.
Separate paired199caseHTTP/core samples after3warmups/profile, with debugHTTPenabled and top5
debugcandidates; resolvercandidate limit stays25, coreoutputlimit5. Defaultcanonicalreference199calls
are correctnessonly, not a newdefaultcostbenchmark. Untimedserving/coreinitialization is disclosed.
Alternate profile order by caseindex to reduce fixed-orderbias. Record everyrawduration/error/status,
revalidation stage, corpus142/indexcounts/environment/SQL/network scope and nearest-rank p50/p95.
Proposed ceilings in protocol-draft are engineeringbudgets needingapproval, not observedmetrics.
No synthetic3000storage experiment:current142-onlysource/count contract cannot accept thatcorpus.
T49.4packaging/closure and future3k/productiondatasets stayseparate.

## Alternatives and decision

Startup-only DB hydration is cheaper but would remainhealthy during DBloss/corruption; reject for
this explicit failclosed readiness contract. Perquery SQLvector retrieval/ANN introduces candidate
admission/fusion/cost changes and newindex evidence; defer rather than calling hydration SQLRAG.
Editingoldservice/config is concise but invalidates frozen source-bound evidence; use compositional
factory/newprofile. Fullsnapshot requestprobes costmore than header-only checks but catch childdata
corruption; choose small142scope now, measure before suggesting10×optimization. Approval pending.
