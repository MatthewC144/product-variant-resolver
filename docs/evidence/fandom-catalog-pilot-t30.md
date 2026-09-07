# T30 Hot Wheels Wiki Catalog Pilot Evidence

> Date: 2026-09-07
> Mode: Lite / review-only external-data pilot
> Dataset: `fandom-hot-wheels-2025-pilot-r790665-v1`

The source probe first attempted the Wiki robots endpoint, which returned HTTP 403. The work did
not interpret that response as permission and did not fall back to HTML crawling. One identified
MediaWiki `siteinfo` request succeeded and reported `CC-BY-SA`; one revisions request then returned
the entire “List of 2025 Hot Wheels” wikitext with revision `790665`, timestamp
`2026-07-17T05:50:26Z`, and page ID `161422`. The response was approximately 93 KB, so no per-item
requests were needed.

The importer froze the raw revision and selected the first 100 valid rows from the main sortable
table. Normalization removed presentation markup, discarded the photo cell, separated suffixes such
as “2nd Color” from the casting name, and retained source templates as markers. It did not request
images or infer colors from their filenames.

Validation reported:

| Check | Result |
|---|---:|
| Records | `100` |
| Unique toy numbers | `100` |
| Sequential source rows | `1–100` |
| Explicit variant notes | `45` |
| Unknown/null colors | `100` |
| Canonical UUID promotions | `0` |
| Raw SHA-256 | `67521e8544de2dd15527e6d2234598c7c70a1e6d9e6597fde06c88bf95854510` |
| Normalized SHA-256 | `e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6` |

Every normalized row repeats the frozen page URL, revision, timestamp, and license. Every row is
`needs_canonical_review`, has `canonical_uuid=null`, and states that it is excluded from canonical
identity, evaluation, and training. The complete host suite passed 79/79, and the dedicated frozen
validator passed. Python compilation and `git diff --check` also passed.

Safety measures include a fixed HTTPS API origin, URL-encoded page input, an identified User-Agent,
a 30-second request timeout, a 3 MB response cap, strict API shape checks, an exact expected-license
check, only two network requests, no media download, and an offline `--raw-input` regeneration
path. This is implementation evidence rather than a formal security or legal sign-off.

The pilot is not yet eligible for PostgreSQL ingestion. The Wiki table does not provide a reliable
text color field, and a row represents a release/variation rather than automatically proving a new
casting identity. Human review and deterministic promotion rules must be agreed before any of these
100 records can change resolver output. The next scale step must reuse frozen revisions and remain
bounded; recurring unattended crawling is outside this milestone.
