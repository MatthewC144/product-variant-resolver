# T38 Evidence — Priority-2 Batch-02 Owner Decisions

## Claim boundary

T38 records the project owner's approval of the exact T37 batch-02 proposal: nine
`create_new_casting` family decisions and one `hold` for `Batman and Robin Batmobile`. It does not
approve an individual release/color identity, mint a catalog ID or canonical UUID, write
PostgreSQL, change Dual-RAG runtime behavior, or create evaluation ground truth.

## Result

The separate decision file covers all ten research packets exactly once and records
`project_owner`, a UTC timestamp, conversation provenance, written family-specific reasons, direct
research/source references, `casting_family_only` scope, and `variant_decision=hold`.

Applying it to the checksum-verified T36 queue produces a new cumulative checkpoint:

| State | Count |
|---|---:|
| Completed family decisions | 24 |
| Pending family decisions | 29 |
| Existing-family merges | 4 |
| Accepted new casting families | 18 |
| Held family decisions | 2 |
| Held Wiki release variants | 46 |
| Promotion-eligible families | 0 |

All four priority-1 decisions, all ten batch-01 decisions, and their two prior history records are
unchanged. The new owner decision is appended as history entry three.

## Implementation evidence

`apply_fandom_priority_two_decisions.py` now accepts batch 01 or 02. Batch 02 binds the latest
cumulative queue, T37 research packet, manifest, and owner-decision file. The applier requires
complete unique packet coverage, recommendation-matching outcomes, direct packet evidence,
family-only scope, held variants, and sufficient source evidence for every creation. It deep-copies
the upstream queue, appends history, recalculates counts, and writes new batch-specific JSON,
Markdown, and checksum-manifest outputs.

The default remains batch 01, and its frozen output still regenerates byte for byte. The extension
therefore does not rewrite the earlier checkpoint.

## Verification

- Combined batch-01 and batch-02 focused decision tests: 12/12 passed.
- Changed batch-02 outcome: rejected as expected.
- Incomplete batch-02 coverage: rejected as expected.
- Reused prior decision-batch ID: rejected as expected.
- Deterministic batch-01 `--check`: passed.
- Deterministic batch-02 `--check`: passed.
- Batch-02 cumulative queue SHA-256:
  `81911e948fd00e76e6da7255ab1174c1697871ac59c3bf674dc5bae645fbc497`.
- Batch-02 adjudication report SHA-256:
  `f6bad5ae831d17bf1ab279c55a46a0dfe176755acfb8c20f512c504af884a392`.
- Owner decision file SHA-256:
  `7350ad739d80999690a74ca1713e86e9509f3c88b038158da45a25e67f094481`.

The final repository-wide verification count is recorded in the QA review and Project Log after
the complete Lite gate runs.
