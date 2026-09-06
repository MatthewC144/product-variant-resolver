# Human-backed catalog draft — v1

## Result

The builder converted all 101 confirmed records from `human-labeled-real-noisy-v1` into a separate
human-backed catalog draft. Exact normalized brand/casting pairs produced 97 casting entities.
Exact normalized series/variant pairs within those castings produced 100 provisional variants.

One duplicate group contains two independently reviewed `1970 Chevrolet Chevelle SS` cases with
the same `Premium` / `Premium, Fast and Furious` structured labels. The builder merges those two
records into one provisional variant while preserving both source case IDs, both human names, and
both pricing keywords. The three `83 Chevy Silverado` records and two `Toyota Supra` records remain
separate variants because their reviewed variant labels differ.

## Identity and provenance policy

Casting and provisional-variant UUIDs are deterministic UUIDv5 values derived from normalized
structured keys and a fixed catalog namespace. Human-readable IDs are derived from the same keys.
Brand display casing is generated consistently from normalized tokens while original reviewed names
remain preserved as aliases. The manifest freezes both the input dataset and generated catalog
checksums.

Every provisional variant is marked `needs_canonical_review`. The draft is eligible for sparse and
dense candidate retrieval and for a future review UI, but is excluded from canonical API responses,
canonical-resolution metrics, calibration training, and threshold selection. Missing structured
attributes are not inferred from free text.

## Verification

The central validator checks checksum linkage, 97/100 counts, unique casting and variant IDs, exact
coverage of all 101 case IDs, and the review status of every provisional variant. Focused tests also
verify deterministic regeneration, exact duplicate preservation, and that similar names such as
`Dodge Challenger`, `18 Dodge Challenger SRT Demon`, and `ICE CHARGER` remain distinct.
