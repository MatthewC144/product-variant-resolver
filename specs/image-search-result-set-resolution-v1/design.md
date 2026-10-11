# Image-search result-set resolution v1 — Design

## Overview

The existing Product Variant Resolver benchmark evaluates one result title at a time. The previous
FlipRadar project received several Serper Lens hits for one screenshot before identity
normalization. This milestone adds an auxiliary offline dataset so a later experiment can compare
top-title, deterministic consensus and learned result-set aggregation fairly. It does not change
the resolver's runtime architecture or API contract.

## Architecture

```text
frozen development identity
       |
Serper Images lookup (temporary URL only)
       |
Serper Lens, at most 10 title-like hits
       |
raw title + conservative cleaned title
       |
minimal versioned result-set dataset

Images, URLs, payloads, API key, timings and collector checkpoints -> deleted
```

## Dataset interface

Each record contains:

- stable dataset-local record ID;
- origin membership (`positive_development` or `no_match_development`);
- catalog-relative truth and challenge type;
- ordered `results`, each containing only `raw` and `cleaned` text;
- `expected_casting` and the frozen `expected_full_identity`.

The dataset top level binds the catalog and both parent query datasets by SHA-256. Rank is implicit
in list order. Empty result lists are valid and measurable provider failures.

## Cleaning contract

Cleaning is deliberately conservative: Unicode/whitespace normalization plus removal of obvious
trailing marketplace/page wrappers. It never deletes numeric or product tokens based on a noise
dictionary. The raw form remains primary because the prior four-arm development result showed that
aggressive cleaning reduced exact-release Top-1 by six percentage points for both sources.

## Error handling

Transient HTTP and rate-limit errors receive bounded retries. A permanent Images or Lens failure
produces an empty result set for that frozen target. Schema drift, changed parent hashes, duplicate
membership, unexpected holdout IDs, non-HTTPS temporary image references or secret-like fields in
the final artifact fail closed.

## Security notes

The collector reads the existing server-side key from the predecessor project's `.env` without
printing or copying it. The key is held in process memory only. Provider responses and image URLs
are never written to the final dataset. The temporary collection directory is Git-ignored and
removed after validation.

## Testing strategy

Tests validate exact 100/40 membership, holdout exclusion, expected identity parity, ordered
raw/cleaned pairs, permitted empty results, URL/secret-field rejection, stable parent hashes and a
dataset directory containing only `dataset.json`.

## Decision

Freeze auxiliary result-set evidence before designing any optional aggregation experiment. This
supports upstream transfer research while preserving the current single-title resolver, Dual-RAG,
ranking and calibration architecture unchanged.
