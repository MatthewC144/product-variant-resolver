# RHB-T5 output-blind query authoring readiness

Date: 2026-10-04
Mode: Lite / Lean Industrial
Verdict: **BLOCKED — CAPACITY PASSES, AUTHORING BOUNDARY DOES NOT YET PASS**

Historical note: this document records the initial readiness result. The projection, publication and
split-contract blockers were later repaired; see
`docs/evidence/representative-hard-benchmark-query-pre-authoring-repair.md`. The original hash and
findings remain unchanged as an audit checkpoint.

## What was validated

The new read-only validator rechecks the frozen T1 inventory and manifest, the exact T3 source
decision overlay, its revision-bound Wiki dependency, the CAR-T6 authority/manifest, and the raw
hashes of the historical RHB-T4 checkpoint. It then inspects only structural properties of the
existing human-name dataset and confirms that no query-pack, query-pack manifest, label or held-label
artifact already exists.

The validator does not import the resolver/service, call retrieval, use a browser or network client,
or write any data. Two identical runs produce the same hash-bound report:
`9a2f5491a6c22c097eaf8bd913c53a46dab71068b1484906f91c48f7b030c840`.

Six direct readiness tests and 76 related RHB/CAR contract tests pass (`82 passed`). Strict MyPy
reports zero issues across the benchmark contract, readiness and CAR-T6 re-audit modules; Ruff,
format and diff checks also pass. A full-repository run was observed without failures through 10%
but was manually stopped because unrelated long-running evaluation tests made it disproportionate;
this evidence therefore makes no new full-suite claim.

## Measured result

| Check | Result | Meaning |
|---|---:|---|
| Human source records | 101 | Matches the frozen T1 inventory and raw SHA-256 |
| Nonblank query texts | 91 | Ten source rows have no usable initial query text |
| Unique nonblank query texts | 91 | Enough capacity for the exact 60-case target |
| Candidate shortfall | 0 | Source quantity is not the blocker |
| Rows with pipeline outputs | 101 | Raw source cannot be handed directly to an author |
| Rows with human-label fields | 101 | Labels must be stripped from the authoring view |
| Rows with nonempty failure categories | 99 | Historical outcome-derived hints must also be stripped |
| CAR-T6 exact authority | 20 variants / 7 families | The 20/4 authority Gate passes with zero shortfalls |
| Existing query/label artifacts | 0 | No unauthorized downstream artifact was found |
| Network/resolver/benchmark-label use | 0 / false / false | This was readiness validation, not evaluation |

## Why the Gate remains blocked

First, `data/human_labeled_names.json` colocates `initial_name` with historical pipeline outputs,
human labels and failure categories. Although the count can be measured mechanically, a query author
must never receive that full object. A deterministic private projection must expose only an opaque
source reference and the raw query text, must be Git-ignored, and must be validated to contain none of
the output/label fields. Because this readiness session inspected the source schema, it is explicitly
not eligible to become the later authoring session; authoring must start from the clean projection in
a fresh context.

Second, the T3 decision permits human query rows only under `local_only`; public Git may contain only
safe aggregate metadata. The current T5 task still names a tracked raw `query-pack.json`, so the
publication path must be split into a private raw pack and a public checksum/count/coverage manifest
before authoring.

Third, `BenchmarkQuery.split` is currently required during T5, while the approved task sequence
assigns family-safe Development/Test splits in RHB-T7 after owner labeling. Filling `split` during T5
would prejudge a later phase and could cause group leakage. The query contract must defer split to the
separate `SplitArtifact` produced by RHB-T7.

Finally, CAR-T6 explicitly retains `RHB_T5`, `query_pack_authoring` and `label_authoring` as prohibited
next steps. No separate RHB-T5 Owner Gate artifact exists. Readiness is therefore
`blocked_pending_pre_authoring_repairs_and_owner_gate`, not an authorization.

## Required next action

The next implementation slice is limited to pre-authoring safety repair:

1. define and test the private output-blind source projection and its Git-ignore boundary;
2. change the query contract so T5 does not assign an RHB-T7 split;
3. revise the artifact plan so raw local-only queries never enter public Git;
4. rerun this readiness validation; and
5. only after those checks pass, present a separate exact RHB-T5 Owner Gate.

Challenge coverage, duplicate-evidence grouping and the final 60-case composition remain unverified
until a newly authorized, output-blind authoring session exists. No query was selected or labeled in
this step.
