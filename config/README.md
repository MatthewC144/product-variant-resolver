# Public Configuration

This directory contains versioned, non-secret configuration and selection artifacts.

- `models.example.json`: example local model configuration; no credentials.
- `neural-reranker-comparison-v1.json`: frozen comparison configuration.
- `domain-ranker-selection-*.json`: selection authorization/result bindings.
- `human-knowledge-retrieval-v4.json`: selected Human Knowledge retrieval configuration.

Configuration presence is not runtime activation. The default settings remain defined in
`src/product_variant_resolver/config.py`, and eligibility checks are enforced in `service.py`.
Secrets belong in local environment variables or ignored `.env`, never in this directory.

