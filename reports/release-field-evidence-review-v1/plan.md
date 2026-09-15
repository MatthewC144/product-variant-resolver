# Release field-evidence review plan v1

This is an offline review workload,not a verified variant dataset. All100 source releases
remain held and canonical UUID/variant-equivalence fields remain null.

## Current evidence gap

The plan covers 100 source rows across 53 casting families.
Color/wheel/tampo are unknown for 100/100/100 rows. 45 rows have a literal variant note,
but notes such as `2nd Color` or `Zamac` do not reveal the actual physical color.

## Proposed first manual batch

Review 4 complete families / 11 rows (limits5/15).
The selection maximizes different evidence problems; it is not an accuracy sample.

| Family | Casting | Family context | Rows | Why included |
|---|---|---|---:|---|
| `fandom-family-174efb9bce3a441e` | Lamborghini Huracán Sterrato | create_new_casting | 3 | family_decision:create_new_casting, second_color_marker, series_divergence, third_color_marker, three_source_rows |
| `fandom-family-b60363832032d566` | Subaru BRZ | merge_existing_family | 3 | family_decision:merge_existing_family, zamac_marker_without_verified_color |
| `fandom-family-369b0be5855c0a1c` | Nissan Skyline 2000GT-R LBWK | hold | 3 | family_decision:hold |
| `fandom-family-18e55e067083dbd1` | '87 Audi quattro | create_new_casting | 2 | multiple_rows_without_variant_note |

## Human review rules

For every row,open the exact evidence pointer and confirm fields independently. Preserve null as
unknown; record disagreements as conflicted. Compare same-casting siblings together,but choose
same release,different release,or unresolved only from attributable evidence. A family merge/new
casting decision never approves color,wheel,tampo or release equivalence.

No new source access was performed. Historical licensing metadata is retained but current rights
remain unverified. New collection belongs to VAR-PLAN2; identity and evaluation belong to VAR-PLAN3.
