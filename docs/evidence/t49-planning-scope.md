# T49 planning checkpoint — source/model scope

Date:2026-09-14. Lite planning only; engineering implementation/model quality NOT EVALUATED.
Upstreamaf27dfe permits design, not database/source/promotion writes. Working tree was clean first.

Actual read-only source audit:

| Source | Observed scope | SHA-256 |
|---|---|---|
| data/human_backed_catalog.json | 97castings,100provisional groups | d29b69cde8099cb229136a73b893ca99b6313d9652ead5ff4aea48c20242e74f |
| data/review_family_knowledge.json | 42typed accepted families | 8615cbb99b453673599e1f9baf54f6900314d7ba64e53a31ea7891c71810b9d7 |
| data/review_family_registry.json | 42new/4merge/7hold governance | 3f289b802cc2e8280ed5c3586d87cfabbee7ce37b10ae79504b5aa6b8837367d |
| pilot-2025/normalized.json | 100records;100color null;no wheel/tampo dedicated fields | e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6 |

`jq` count/key checks and SHA-256 reads produced the table above; no values/labels were added.
Current `ProductView`/canonical0001 migration and seven-field `IDENTITY_FIELDS` lack wheel/tampo
fields; legacy identity must not be changed in place. Structured retrieval already uses supported
color/year/series/number evidence, but it cannot make absent source attributes or full variant
truth appear. The design proposes observation/evidence state and future versioned identity work,
not inventing those values or claiming already reviewed100release variants.

Current committed benchmark and final raw/Markdown checks PASS without retrieval. Existing411
regression evidence is upstream; this docs-only planning checkpoint has no newly implemented
runtime, migrations, tests, persisted documents, approved releases or data expansion to measure.

Read-only browsing check: official MediaWiki API etiquette accessible; Fandom licensing and
Hot_Wheels page fetches returned402 from the browsing service. No crawler/API probe/bypass or
media download executed. Do not infer website-wide permission or denial from this tool response;
current source-specific access/terms remain a future precollection gate. General serial reads,
descriptive User-Agent and caching guidance verified at
[MediaWiki API etiquette](https://www.mediawiki.org/wiki/API:Etiquette), accessed2026-09-14.
Historical pilot license/attribution stays as recorded, not a current legal-clearance claim.

Draft requirements/design/tasks separate snapshot persistence from release review and canonical
promotion. R1–R14 have proposed observable acceptance/tasks; none has owner approval yet. Next
confirm requirements, then design, then tasks. No subagents, new product code or external mutation.
