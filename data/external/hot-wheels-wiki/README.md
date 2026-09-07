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
