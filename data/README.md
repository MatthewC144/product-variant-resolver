# Data Map

This directory mixes runtime inputs with frozen evaluation evidence. Every subdirectory has a
different authority level; file presence alone does not make a row canonical truth.

## Runtime and reviewed knowledge

- `catalog.json`: catalog used by the default resolver.
- `human_backed_catalog.json`: provisional/reviewed Human Knowledge; supporting evidence only.
- `review_family_knowledge.json`: reviewed family evidence used by the Human Knowledge branch.
- Adjacent manifests bind versions and checksums.

## `evaluation/`

Versioned benchmark inputs, split/authorization manifests, aggregate results, and private-artifact
bindings. The primary current result is
`serper-dual-source-evaluation-v1/raw-pointwise-final-test.json`; most other directories are
historical development, negative experiments, or holdout governance. Start with
[Results](../docs/RESULTS.md), not by comparing filenames.

## `authority-review/`

Owner-reviewed evidence and transitions for the bounded exact-authority subset. It does not promote
the full third-party source to manufacturer or global truth.

## `external/`

Attributed third-party source snapshots and aggregate manifests. Source-specific README files define
provenance and redistribution boundaries.

## Local-only material

Raw XLSX exports, downloaded images, temporary API responses, output-blind workspaces, row-level
private labels/predictions, and collection checkpoints are ignored. Do not add secrets, URLs, or
private collection workspaces to this directory.

