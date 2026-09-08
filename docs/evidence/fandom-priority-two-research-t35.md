# T35 Evidence — Priority-2 Research Batch 01

## Claim boundary

T35 researched the first ten pending priority-2 casting-family items in the adjudicated queue. It
did not record a human decision, create a canonical UUID, write PostgreSQL, change runtime Dual-RAG
behavior, or verify any individual color/release variant.

## Result

The deterministic batch contains ten families and nineteen Wiki release rows. Nine families have a
dedicated Wiki casting page plus at least one non-Fandom exact-name confirmation and therefore
receive a machine `create_new_casting` recommendation. `'55 Chevy` receives `hold`: its Wiki title
is explicitly a disambiguation page for 1982, 1998, and 2006 casting tools, so the staged family
name cannot identify one tool.

Every packet retains `reviewer_confirmation.status=pending`,
`variant_decision=hold`, and `promotion_eligible=false`. Counts are therefore nine proposed
creations, one proposed hold, zero reviewer decisions, and zero promotion-eligible families.

## Source and implementation evidence

The curated source-note input stores HTTPS URLs, publisher/source type, and concise paraphrased
observations. It uses Hot Wheels Wiki casting pages for casting-page classification and separate
publishers including Mattel, Orange Track Diecast, Hot Wheels Collectors News, HW Headline, South
Texas Diecast Collectors, HW Treasure, and SmartWheelers. No images were downloaded.

`build_fandom_priority_two_research.py` verifies the adjudicated-queue checksum, selects the first
ten still-pending priority-2 entries, requires exact ID/name/order coverage, rejects Fandom as an
“independent” source, derives the recommendation from page classification, and emits deterministic
JSON, Markdown, and a checksum manifest.

## Verification

- Focused unit tests: 6/6 passed.
- Deterministic `--check`: passed.
- Invalid same-host independent evidence: rejected as expected.
- Research JSON SHA-256:
  `a802f64478b73a0c40f43c1d43fa44b182ebdbcde9f67d3d0c97f237c92a241c`.
- Markdown SHA-256:
  `acdd94dc89abee72f0c2e197bf4392fc2c13671b2282cc68e5765d6dbca9669f`.

The final full-suite and compilation counts are recorded in the QA review and Project Log after
completion of the repository-wide verification run.
