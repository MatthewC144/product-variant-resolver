# Hot Wheels Wiki text-data attribution

The files below this directory contain or adapt text-table content from the Hot Wheels Wiki at
Fandom. They are kept separate from the repository's synthetic canonical fixture and are not
canonical ground truth or evaluation labels.

## Pilot source

- Work: “List of 2025 Hot Wheels” by Hot Wheels Wiki contributors
- Frozen source revision: [revision 790665](https://hotwheels.fandom.com/wiki/List_of_2025_Hot_Wheels?oldid=790665)
- Page history / contributor attribution: [history](https://hotwheels.fandom.com/wiki/List_of_2025_Hot_Wheels?action=history)
- Source revision timestamp: `2026-07-17T05:50:26Z`
- License reported by the wiki API: `CC-BY-SA`
- License terms: [Fandom Licensing](https://www.fandom.com/licensing)

The `pilot-2025/raw.json` file preserves the source wikitext and revision metadata. The normalized
derivative selects the first 100 valid mainline table rows, removes Wiki/HTML presentation markup,
omits the photo column, separates suffixes such as “2nd Color” into `variant_note`, and adds review
and provenance fields. Unknown colors remain `null`; no values are inferred from filenames or
images. These source-derived data files remain subject to the source CC-BY-SA terms.

No image or other non-text media file was downloaded. Fandom states that non-text files must not be
assumed to use the same license as Wiki text.

## Cross-catalog review

`pilot-2025/review.json` compares all 100 staged rows with the repository's canonical fixture and
human-backed draft. It uses exact normalized brand and casting names only; fuzzy and
identifier-only matching are disabled. An exact match means “review this existing casting family,”
not “promote this release.” All 100 decisions remain `hold_for_human_review` with null canonical
identity. `review-manifest.json` freezes all three inputs and the review output by SHA-256.

`pilot-2025/adjudication-queue.json` then groups the 100 rows into 53 casting-family decisions.
The accompanying `adjudication-queue.md` is the human-readable worksheet, and its manifest freezes
the review input plus both queue outputs. A completed decision must identify the reviewer, time,
reason, and evidence; all checked-in decisions remain pending and promotion-ineligible.

`pilot-2025/priority-1-evidence.md` presents the first four exact family candidates side by side
with their Wiki release rows and retained human-label evidence. Its JSON and manifest preserve the
same comparison for validation. Family merge is a machine recommendation only; all reviewer
confirmations and variant decisions remain pending/held.

`pilot-2025/priority-1-decisions.json` records the project owner's follow-up authorization for the
four family-only merges. `adjudicated-queue.json` is the validated result: four completed family
relationships, 49 pending families, nine held Wiki variants, and zero promotion-eligible families.
The original pending queue stays unchanged as an auditable pre-decision artifact.

`pilot-2025/priority-2-batch-01-source-notes.json` freezes concise, AI-assisted text-source notes
for the first ten pending priority-2 families. The derived JSON/Markdown research packet requires
one dedicated Wiki casting page and exact-name evidence from at least one non-Fandom publisher
before recommending `create_new_casting`. It recommends nine creations and holds `'55 Chevy`
because the source title is a disambiguation page covering three casting tools. These remain
machine recommendations with empty reviewer confirmations; all 19 release rows remain held and no
canonical or PostgreSQL record is created. Linked external pages retain their own terms; the notes
store only URLs and concise paraphrased observations, and no images were downloaded.

`pilot-2025/priority-2-batch-01-decisions.json` records the project owner's follow-up approval of
the nine new-family recommendations and the `'55 Chevy` hold. The derived batch-01 adjudicated
queue preserves the four earlier family merges and reports 14 completed / 39 pending family
decisions, 28 held release variants, and zero promotion eligibility. The validator requires every
research packet exactly once, rejects an outcome that differs from the approved recommendation,
and refuses variant promotion. No canonical catalog or PostgreSQL record is created.

`pilot-2025/priority-2-batch-02-source-notes.json` continues from that cumulative queue and freezes
research for the next ten still-pending families / eighteen release rows. Nine names meet the same
two-source creation-recommendation rule. `Batman and Robin Batmobile` remains held because a
separate 2004 100% Hot Wheels casting tool uses the same display name, so the queued text is not a
tool-unique identity. The batch-02 JSON, Markdown report, and manifest remain machine research:
reviewer confirmations are pending, variants are held, and promotion eligibility is zero.

`pilot-2025/priority-2-batch-02-decisions.json` records the owner's follow-up approval of the nine
creation recommendations and the Batman hold. The derived batch-02 cumulative queue preserves all
three decision batches and reports 24 completed / 29 pending family decisions, 18 accepted new
families, 2 holds, 46 held release variants, and zero promotion eligibility. This is still an
adjudication layer rather than a searchable catalog or PostgreSQL import.

`pilot-2025/priority-2-batch-03-source-notes.json` continues from that cumulative checkpoint and
freezes research for the next ten pending families / eighteen release rows. Every name has a
dedicated Wiki casting page and at least one non-Fandom exact-name confirmation, so the derived
packet proposes ten new casting families and zero holds. The notes preserve related-casting
distinctions for Fiat 500e versus Fiat 500 and for the newer Hirohata Merc versus the earlier `'51
Merc` tool; a differently named predecessor is supporting lineage context, not a same-name
homonym. The JSON, Markdown report, and manifest remain unconfirmed machine research. Every release
variant is held, promotion eligibility is zero, and no catalog or PostgreSQL record is created.

`pilot-2025/priority-2-batch-03-decisions.json` records the project owner's follow-up approval of
all ten batch-03 family recommendations. The derived batch-03 cumulative queue preserves all four
ordered decision events and reports 34 completed / 19 pending family decisions, 4 accepted merges,
28 accepted new families, 2 holds, 64 held release variants, and zero promotion eligibility. The
decision file and derived outputs are checksum-frozen. These accepted family outcomes still do not
exist as catalog entities or PostgreSQL/runtime records.

`pilot-2025/priority-2-batch-04-source-notes.json` continues from the 34-completed / 19-pending
cumulative queue and freezes research for ten families / twenty-three release rows. Eight names
meet the dedicated-page plus non-Fandom exact-name rule. Mazda MX-5 Miata is held because separate
1991 and 2025 1:64 tools share the display name. Nissan Skyline 2000GT-R LBWK is held because the
regular and Tooned same-scale tools share the name; the current toy numbers map to the Tooned page,
but the name-only family key remains ambiguous. The packet treats Nerve Hammer's documented retools
as one continuous lineage and retains the separately suffixed 1:43 Mercedes-Benz 500 E XL page as
scale context. All results are machine recommendations with pending reviewer fields, held variants,
zero promotion, and no catalog/PostgreSQL/runtime mutation.
