# T32 Fandom Human-Adjudication Queue Evidence

> Date: 2026-09-08
> Mode: Lite / human-work preparation
> Queue: `fandom-2025-pilot-adjudication-queue-v1`

T32 converts the 100 row-level T31 results into 53 stable casting-family review items. Every source
record ID and row appears exactly once. Repeated base, second-color, and other release rows remain
nested under one family so a reviewer does not repeatedly decide the same casting relationship.

| Queue state | Count |
|---|---:|
| Source rows represented | `100` |
| Distinct family decisions | `53` |
| Priority 1 exact existing-family candidates | `4` |
| Priority 2 possible-new families requiring research | `49` |
| Completed human decisions | `0` |
| Promotion-eligible families | `0` |

The priority 1 groups are `'67 Chevy C10`, `Purple Passion`, `Subaru BRZ`, and
`Tesla Model S Plaid`. Priority only controls review order; it is not an approval. Each queue item
retains candidate IDs, a machine-authored suggested action and reason, all contributing Wiki rows,
and an empty reviewer-decision object.

The decision contract permits `merge_existing_family`, `create_new_casting`, `hold`, or `reject`.
A completed decision must include `decided_by`, `decided_at`, a written reason, and evidence
references. Pending items are explicitly promotion-ineligible. New-casting decisions additionally
require independent source confirmation, while family merges still do not establish color or
release-variant identity.

The queue SHA-256 is
`638f35d36bbf25ec0767210c038e6ee3c1e097f4f3e67d78a9bbef4a8dd45558`; the readable worksheet
SHA-256 is `748ce49c0c54afe0b60e2cc7d25275a990462f8116060f105059c4dc000acd36`.
The manifest also freezes the T31 review and review-manifest inputs.

Five focused tests passed for complete grouping, stable family IDs, priority ordering, candidate
boundaries, the decision contract, all-pending safety, checksums, and deterministic regeneration.
The complete host suite passed 89/89. The `--check` command reproduced the JSON, Markdown, and
manifest byte for byte. Fixture validation, Wiki pilot validation, T31 review verification, Python
compilation, both Compose configurations, and patch whitespace checks passed.

T32 performs no network call, database write, canonical-catalog change, AI evaluation, or human
decision. It makes the next human step auditable; it does not mislabel an AI recommendation as
human verification.
