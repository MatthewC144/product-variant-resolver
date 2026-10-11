# Image-search result-set resolution v1 — Requirements

Date: 2026-10-11. Mode: Lite / Lean Industrial. Status: complete.

## Product goal

Bridge the real FlipRadar workflow boundary: a livestream frame is sent to image search, the
provider returns several noisy title-like results, and the resolver must convert that evidence into
one catalog identity suitable for a downstream pricing query. This version first freezes the
multi-result development evidence; it does not activate a runtime endpoint or open policy holdouts.

## Observable requirements

- **ISRS-R1 — Real boundary.** WHEN the dataset is created, THE SYSTEM SHALL represent one image
  search as an ordered set of up to ten title hits rather than one preselected title.
- **ISRS-R2 — Frozen development membership.** WHEN targets are selected, THE SYSTEM SHALL use only
  the existing 100 positive development identities and 40 no-match development identities, and
  SHALL NOT use the 50-target opened ranking final or the 40-target fresh policy holdout.
- **ISRS-R3 — Exact labels.** WHEN a record is written, THE SYSTEM SHALL retain both casting-level
  truth and the original complete expected identity. No legacy casting-only label may be promoted
  to a full release answer.
- **ISRS-R4 — Raw and cleaned evidence.** WHEN a provider title is admitted, THE SYSTEM SHALL keep
  its raw text and a conservative cleaned form together, preserving years, series, collector
  numbers, toy identifiers, colors and edition signals.
- **ISRS-R5 — Minimal public artifact.** THE final tracked dataset SHALL contain only frozen parent
  bindings, truth, expected identity and raw/cleaned result text. It SHALL NOT contain API keys,
  images, image URLs, thumbnails, provider payloads, collection timestamps or local paths.
- **ISRS-R6 — No quality replacement.** IF a target returns no usable Lens titles, THEN THE SYSTEM
  SHALL preserve that target with an empty result set rather than replace it with an easier target.
- **ISRS-R7 — Collection isolation.** WHILE collection runs, temporary code and checkpoints SHALL
  remain outside the final dataset directory and SHALL be deleted after deterministic validation.
- **ISRS-R8 — Downstream boundary.** This task SHALL NOT fit a result-set aggregator, calibrate a
  policy, score a holdout, call a pricing API or change FastAPI runtime behavior.
