# Family Retrieval Holdout v1

This directory is the test-only handoff boundary for T48. The official query pack, pre-score
manifest, project-owner decisions, labeled benchmark, and benchmark manifest are now frozen.
Retrieval results do not exist yet.

The files must be created in this order:

1. T48.2 authored `query-pack.json` without running or viewing Human Knowledge retrieval.
2. `build_family_retrieval_benchmark.py --freeze-query-pack` validated the 105 cases and wrote
   `query-pack-manifest.json`, which binds their checksum and the frozen retriever inputs.
3. The project owner reviewed the frozen cases and T48.3 recorded `owner-decisions.json` against
   that exact query-pack checksum.
4. The builder produced `benchmark.json` and `benchmark-manifest.json` only after every structural,
   leakage, approval, version, checksum, and usage-boundary check passed.

All cases belong only to the `test` split. They cannot be used for training, calibration, threshold
selection, query rewriting, retriever tuning, canonical responses, release-variant truth,
PostgreSQL ingestion, or production-accuracy claims. A failed v1 result may diagnose a weakness,
but any changed retriever needs a newly authored holdout for final evidence.

No live marketplace or Wiki request is part of this workflow. Query text is synthetic, and neither
the authoring script nor the builder calls the retriever.
