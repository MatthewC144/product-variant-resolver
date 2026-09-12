# Family Retrieval Benchmark Freeze — T48.3 Evidence

> Mode: Lite / Lean Industrial
>
> Status: PASS for owner approval and unscored benchmark freeze
>
> Date: 2026-09-12

## Authority and immutable input

The project owner was shown the complete human-readable 105-case query/reference pack, its test-only
purpose, the absence of retrieval output, and SHA-256
`26e244c04325f7909fb222b6cdd32ee2301253db17f0b8b97cf2f63ac4358733`. The owner's next instruction
was to proceed. T48.3 records that bounded approval against the unchanged hash at
`2026-09-12T16:50:40Z`; it does not extend to canonical data, release variants, PostgreSQL, tuning,
or production use.

## Decision artifact

`owner-decisions.json` contains exactly 105 sorted decisions and SHA-256
`d22b96bb16cd9cb9e19f4a4723a41b653da7b4961b5b588f6f636e1b37e1bad1`. Every item records
`decided_by=project_owner`, the UTC timestamp, `decision=approve`, a non-empty reason, and one of the
four validated expected-label shapes:

- 84 positive cases expect the referenced `review_family` ID.
- 4 merge controls expect the registry's existing provisional-variant `casting_id` and forbid a
  duplicate review-family ID.
- 7 hold controls set `expected_materialized=false` and forbid their held review-family ID.
- 10 unrelated controls expect zero candidates and retain their proven zero-token-overlap flag.

The reproducible decision script hardcodes the approved query checksum before it reads or writes an
approval. If a query byte changes, decision generation/checking fails. The generic benchmark
validator independently rejects partial, duplicate, pending, reordered, stale, unknown, or
type-inconsistent decisions.

## Frozen benchmark

The validated builder produced `benchmark.json` at SHA-256
`440246fb6a3b38f56fc25c1ec939d53d6cfc4457fed738aad561899325808afd`. Its manifest freezes every
query, decision, registry, projection, catalog, and code/version input. Accounting remains exactly
105 total, 84 positive, 4 merge, 7 hold, 10 unrelated, 42 positive groups, and zero train/dev.

This is a labeled test contract, not an evaluation report. Static inspection confirms there are no
candidate lists, sparse/dense/RRF ranks or scores, metrics, gates, verdict, canonical decisions, or
PostgreSQL outputs in the benchmark. Neither the decision recorder nor benchmark builder imports or
calls the Human Knowledge retriever.

## Verification and next gate

The focused contract suite passes 10/10, including actual-artifact reconstruction and read-only
checksum checks for the owner decisions, benchmark, and manifest. The complete repository suite
passes 194/194 in 2.203 seconds on the final tree. Python compilation, owner/benchmark reproduction,
the configured 100-character code-line check, `git diff --check`, and repository-root scope check
also pass. Ruff is unavailable on this host, so no Ruff result is claimed. The suite emits only the
known non-failing Starlette legacy-`httpx` environment warning.

T48.3 passes only the label-integrity and benchmark-freeze boundary. T48.4 is the first task allowed
to retrieve candidates and calculate the precommitted Recall@1/5, MRR@5, style/family coverage, and
control gates. Its result must remain truthful even if it is FAIL.
