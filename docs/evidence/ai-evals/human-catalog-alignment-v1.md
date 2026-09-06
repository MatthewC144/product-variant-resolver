# Human-label to fixture-catalog alignment — v1

## Result

The deterministic alignment evaluated all 101 records in `human-labeled-real-noisy-v1` against the
120-product `fixture-v1` catalog. It produced:

| Status | Count | Meaning |
|---|---:|---|
| `mapped` | 0 | One canonical UUID was supported by exact structured evidence. |
| `casting_family_only` | 2 | Brand and casting matched exactly, but no unique variant was supported. |
| `unmapped` | 99 | The fixture catalog has no exact brand/casting family. |

Both family-only records are `Toyota Supra`. Each points to 12 possible synthetic catalog variants,
and the human series/variant labels do not uniquely match one of them. Assigning a UUID would
therefore fabricate precision. All 101 records correctly retain null canonical identity.

## Method and boundary

`scripts/align_human_labeled_names.py` normalizes Unicode and punctuation for exact comparison; it
does not perform fuzzy matching. Family alignment requires exact brand and casting. Canonical
variant alignment additionally requires exact series plus one exact discriminator among catalog
color, edition, or rarity tier, and the surviving candidate must be unique.

The alignment manifest freezes SHA-256 values for the reviewed-name dataset, catalog, and generated
alignment. The central fixture validator checks these links, complete case-ID coverage, valid
statuses, and that every non-mapped record has null UUID and slug.

This artifact measures catalog coverage, not resolver quality. Its 0% canonical mapping rate must
not be combined with fixture-v1 accuracy. The next data step is a reviewed, provenance-backed
catalog expansion, not a looser matching threshold.
