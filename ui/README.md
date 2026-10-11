# Local Demo UI

This directory contains a minimal static interface for local resolver demonstrations. It is served
by the FastAPI application and does not have a separate frontend build pipeline.

The UI displays resolver outcomes and bounded debug evidence when enabled. It does not capture
livestream frames, call image search, query prices, activate neural checkpoints, or prove a deployed
product experience.

It requests same-origin `POST /resolve` with `debug=true`, renders API-supplied values through
`textContent`, and clamps candidate depth to the contracted 1–25 range. Serving it from another
origin would require a separately reviewed CORS policy.

For the API contract, start with [`api.py`](../src/product_variant_resolver/api.py) and the
[Code Tour](../docs/CODE-TOUR.md).
