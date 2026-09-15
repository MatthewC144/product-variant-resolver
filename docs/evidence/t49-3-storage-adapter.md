# T49.3 HSP-2 — Storage adapter and source-freeze evidence

2026-09-14. Lite, main agent; no subagents. Verdict:HSP-2 PASS for code/private mocks/source freeze.
Owner「執行下一步」followed the HSP-1 completion handoff naming HSP-2. It does not authorize HSP-3.

## Observable implementation

`human_knowledge_storage_profile.py` accepts only strict versioned file or PostgreSQL profiles,
rejects duplicate/unknown/missing fields, latest/fallback, changed protocol/math/snapshot/source bytes,
unfrozen runtime state and non-disposable DB names. It never stores a DB URL in profile/provenance.
Startup hydrates the exact142 typed docs (100provisional+42family) into the existing v4 in-memory
retriever. File mode rebuild-validates plan+12sources; PostgreSQL mode invokes the existing repository's
whole-snapshot repeatable-read/read-only path. Every probe rereads and byte-compares the whole selected
snapshot. Any failure latches until process restart; no fallback/retry/repair method exists here.

`human_knowledge_storage_app.py` is a separate entrypoint composed from existing `api.create_app` and
`ResolverService`; old sources are unchanged. Existing validation occurs before storage-backed resolve,
so malformedJSON400, wrongtype415, blank/501char/debug-disabled422 never probe. Valid calls probe then
delegate. Debug adds only `human_storage_integrity` timing plus storage version/SHA in existing maps;
nondebug canonical bodies stay unchanged. Health probes and adds versioned `human_knowledge_storage`;
the old `database` dependency still means canonical backend. Failure clears app state and yields503
without identity. Without an explicit profile, experimental app is not-ready while original app is ready.

## Tests and honest failures

Final focused:`PYTHONPATH=src .venv/bin/python -m pytest` on the three new files:55PASS/1existing
warning,4.29s. Full suite:544PASS/1warning,18.61s. Ruff F/I, isolated strict MyPy on3new product/scripts,
compileall and whitespace PASS. HSP-1/local142/T49.2 stored SQL/final stored-result checks also PASS
without new SQL or final retrieval. Original frozen source diff is empty.

Development failures were retained and fixed before accepted freeze:

- pytest reserved parameter prevented first collection and static checks found typing/import issues;
  names/types were corrected without changing behavior.
- 37PASS/1FAIL used an invalid test assumption that short`Chevy Nomad` must be canonical matched;
  it was replaced by the existing catalog-specific `2022 Chevy Nomad Red #101`. Product logic unchanged.
- Runtime-source tests initially50PASS/4FAIL:producer captured dirty/current hashes without proving all
  sources matched one commit. Generator now compares every bound file to the producer commit first.
- Candidate1 (`5d9e2f3`, manifest`ddf50a…`) passed its then-current checks but task review found no
  separate versioned storage dependency in health. It remains under `runtime-source-freeze/` plus
  `SUPERSEDED.md`; no result used it. Candidate2 adds the wrapper/test and is the accepted source freeze.

## Accepted source freeze and boundaries

Accepted directory:`data/evaluation/human-storage-profile-development-v1/runtime-source-freeze-v2/`.
Producer commit:`bd2a8387385a960add42d9669a77f33132bccdec`; producer SHA`c84daf…`.
42source hashes include both adapters, their internal runtime dependencies, storage/math protocols,
canonical catalog, exact plan+12inputs and dev pack. Adapter manifest SHA:
`93a8b6318f6770f9901aff210a320d315c9ba66c356b40df2762ad398d2a91f1`.
Files:manifest`ebd0fe…`,template`821b38…`,protocol binding`ee27ce…`,report`913471…`.
Template is deliberately non-runnable; runtime images=null,ready=false,new outputs/execution=false.

Fake DB proves orchestration and full-read/latch semantics only. No real database, role permissions,
containers, HTTP server process,199case outputs or latency measurements were run. SQL SELECT-only
denials, exact199 file/DB parity and full fault matrix belong to separately authorized HSP-3; costs to
HSP-4. Color/wheel/tampo identity and3k expansion remain excluded. FullT49.3/T49.4 are incomplete.
