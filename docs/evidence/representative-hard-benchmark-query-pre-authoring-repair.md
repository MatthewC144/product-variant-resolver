# RHB-T5 pre-authoring safety repair

Date: 2026-10-04
Mode: Lite / Lean Industrial
Verdict: **PASS — READY FOR A SEPARATE OWNER GATE, NOT AUTHORIZED FOR AUTHORING**

## Problem closed

Initial readiness proved that 91 unique real query candidates exist, but the only source file placed
each query beside historical pipeline output, human labels and failure categories. It also showed a
publication mismatch—the raw rows are local-only while the task named a tracked query-pack path—and
a phase mismatch because `BenchmarkQuery` required an RHB-T7 split during RHB-T5 authoring.

The repair closes all three engineering gaps without choosing a case, writing a query pack, creating
a label, invoking the resolver or granting RHB-T5 permission.

## Private projection and public boundary

`build_representative_hard_benchmark_query_projection.py` validates the frozen T1 inventory and T3
decisions, reads only `case_id` and nonblank `initial_name`, rejects duplicate IDs/text, and builds 91
ordered records. The strict row contract allows exactly `source_record_ref` and `query`; unknown
fields such as `pipeline_outputs` or `human_label_casting` fail validation.

The projection lives at the Git-ignored
`data/evaluation/representative-hard-benchmark-v1/local-query-authoring-v1/output-blind-source.json`.
Its directory is `0700`, the file is `0600`, and the public manifest is `0644`. Creation followed by
check replay returns `created / unchanged`. Git ignore resolves to the exact dedicated rule.

The tracked `query-authoring-source-manifest.json` exposes only schema, SHA-256, record count, a
non-sensitive aggregate and summary. It contains no row-level query. Its private-byte SHA-256 is
`d5712684cf73c29dd9ea7f385f78c03eb1c8300ce35afd477c0d09ad0d9032dd`.

## Split ownership repair

`split` was removed from `BenchmarkQuery`; Pydantic's `extra=forbid` now rejects anyone attempting to
preassign Development/Test in the T5 query pack. RHB-T7 retains the separate `SplitArtifact`, which
must cover every query exactly once and rejects a family or evidence group crossing splits. Query
authoring therefore cannot hand-pick the Test set before labels and connected components exist.

## Readiness v2 result

The v2 validator rechecks the private projection against its source and public manifest, filesystem
permissions, ignore boundary, CAR-T6 authority, historical audit hashes, source capacity and absence
of query/label artifacts. Its deterministic result is:

```text
status: ready_for_separate_owner_authorization
projection: 91 rows, valid, private and ignored
query contract requires split: false
CAR-T6: 20 exact / 7 qualifying families / 0 shortfalls
RHB-T5 authorized: false
remaining blockers: fresh output-blind authoring context; separate Owner Gate
readiness SHA-256: 5b2582049420406f0acf5577bcca17f22f0834e598e87838c294625cdf300d30
```

The next permitted action is to present a narrowly scoped RHB-T5 Owner Gate. If approved, the 60-case
selection must occur in a fresh context that can access only the query-only projection—not this
inspection/build context and not `data/human_labeled_names.json`.

## Verification

All 99 representative-benchmark projection/readiness/contract/source/CAR tests pass. Strict MyPy
reports zero issues across the benchmark contract, projection, readiness and CAR-T6 re-audit modules; Ruff, format,
compile and diff checks pass. Projection check replay returns `unchanged` twice, readiness v2 is
byte-identical across two runs, the private file is absent from `git ls-files` and positively matched
by `git check-ignore`, and the public manifest has exactly the five approved top-level aggregate
fields. A fresh-clone-shaped state containing the tracked manifest but no ignored projection safely
rebuilds only the private file and leaves public bytes unchanged. No full-repository PASS is newly
claimed by this repair.
