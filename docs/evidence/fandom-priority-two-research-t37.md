# T37 Evidence — Priority-2 Research Batch 02

## Claim boundary

T37 researched the next ten pending priority-2 casting-family items after T36's fourteen completed
decisions. It did not record a human decision, mint a catalog identity, write PostgreSQL, change
Dual-RAG runtime behavior, or verify an individual color/release variant.

## Result

The deterministic batch contains ten families and eighteen Wiki release rows. Nine families have
one dedicated Wiki casting page plus an exact-name confirmation from a publisher outside Fandom,
so they receive machine `create_new_casting` recommendations: `'94 Audi Avant RS2`, `Alpha
Pursuit`, `Bogzilla`, `Crescendo`, `Custom '53 Chevy`, `Custom Cadillac Fleetwood`, `Deora III`,
`DMC DeLorean`, and `Donut Drifter`.

`Batman and Robin Batmobile` receives `hold`. The current mainline evidence and an independent
2025 listing confirm the name, but Wiki also documents a separate 2004 100% Hot Wheels casting tool
G5513 under the same display name. The staged name alone is therefore not tool-unique.

Every packet retains `reviewer_confirmation.status=pending`, `variant_decision=hold`, and
`promotion_eligible=false`. Counts are nine proposed creations, one proposed hold, zero reviewer
decisions, and zero promotion-eligible families.

## Source and implementation evidence

The source-note input records HTTPS URLs, publishers, source types, and concise paraphrased
observations. Corroborating publishers include Mattel Consumer Services, Orange Track Diecast,
164Custom, Hot Wheels Collectors News, Hot Wheels Database, and HW Treasure. No images were
downloaded.

`build_fandom_priority_two_research.py` now accepts an explicit batch selector. Batch 02 verifies
the T36 cumulative queue checksum, takes only the first ten still-pending priority-2 entries, and
therefore cannot silently repeat the completed batch-01 families. The same implementation retains
batch-01 defaults and output text, while adding a fail-closed `homonymous_castings` classification
whose recommendation is always hold.

## Verification

- Batch-01 plus batch-02 focused unit tests: 12/12 passed.
- Deterministic batch-01 `--check`: passed.
- Deterministic batch-02 `--check`: passed.
- Batch-02 research JSON SHA-256:
  `e0814c8017361049c2fa3b712198a22968e9818c2db273c49af668c2639050dc`.
- Batch-02 Markdown SHA-256:
  `86444256ded953b6ed5e329dccfdf531e5f2565df7212370178fb1a45d81a7ca`.
- Upstream T36 adjudicated queue SHA-256:
  `2b82ca5023439857f186aa0ab122f0b4511290bb4d1303ac533df5c96fbc6790`.

The final repository-wide test and validation counts are recorded in the QA review and Project Log
after the complete verification run.
