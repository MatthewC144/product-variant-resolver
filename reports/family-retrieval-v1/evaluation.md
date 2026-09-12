# Human Knowledge RAG v2 — Frozen Holdout Evaluation

> Verdict: **FAIL**
>
> This is a one-time, test-only result. It must not be used to tune the same retriever.

## Evaluation identity

- Benchmark: `family-retrieval-holdout-v1` (105 cases)
- Benchmark SHA-256: `440246fb6a3b38f56fc25c1ec939d53d6cfc4457fed738aad561899325808afd`
- Benchmark manifest SHA-256: `8b173ec0a078e0ba65d74845d1ae182a45c91fd87d41ab14d295eb382618ea31`
- AI-eval record: [`docs/evidence/ai-evals/family-retrieval-holdout-v1.md`](../../docs/evidence/ai-evals/family-retrieval-holdout-v1.md)
- Retriever: `human-knowledge-hybrid-v2`
- Dense representation: `hashing-v1` / 192 dimensions
- Query preprocessor: `signals.extract_signals-v1` (`30195e91d52fb1a5ef3570ce9042fb2a24d9e78ba5475ebe76194937c82e76de`)

## Precommitted gates

| Gate | Actual | Required | Result |
|---|---:|---:|:---:|
| `positive_recall_at_5` | 0.8690 | >=0.8500 | PASS |
| `positive_recall_at_1` | 0.6905 | >=0.6500 | PASS |
| `positive_mrr_at_5` | 0.7738 | >=0.7500 | PASS |
| `lexical_variation_recall_at_5` | 0.7381 | >=0.7500 | FAIL |
| `marketplace_noise_recall_at_5` | 1.0000 | >=0.7500 | PASS |
| `family_coverage_at_5` | 1.0000 | >=0.9000 | PASS |
| `merge_control_recall_at_5` | 1.0000 | =1.0000 | PASS |
| `forbidden_family_hits` | 0 | =0 | PASS |
| `unrelated_non_empty_results` | 0 | =0 | PASS |

## Recomputable raw counts

- Positive Recall@1: `58 / 84`
- Positive Recall@5: `73 / 84`
- Positive MRR@5: `65.0 / 84`
- Family coverage@5: `42 / 42`
- Merge-control Recall@5: `4 / 4`
- lexical_variation Recall@5: `31 / 42`
- marketplace_noise Recall@5: `42 / 42`
- Forbidden family hits: `0` candidates across `0` cases
- Unrelated non-empty results: `0 / 10`

## Error categories

| Category | Cases |
|---|---:|
| `expected_identity_not_retrieved` | 10 |
| `no_candidates` | 1 |
| `none` | 94 |

## Case-level errors (11)

The JSON report retains the complete ordered candidates and scores for all 105 cases. This table is the compact failure view.

| Case | Type / style | Expected rank | Error | Returned identities (rank order) |
|---|---|---:|---|---|
| `fre-positive-174efb9bce3a441e-lexical` | positive_family / lexical_variation | — | `expected_identity_not_retrieved` | provisional_variant:human-hot-wheels-toyota-off-road-truck-silver-series-silver-series, provisional_variant:human-hot-wheels-subaru-brat-hw-off-road-pearl-yellow-kmart-exclusive, provisional_variant:human-hot-wheels-tesla-model-s-plaid-mainline-red, provisional_variant:human-hot-wheels-angry-birds-minion-pig-mainline-angry-birds-minion-pig, provisional_variant:human-hot-wheels-hummer-h1-silver-series-fast-furious |
| `fre-positive-2357e7eb6b4e62b8-lexical` | positive_family / lexical_variation | — | `expected_identity_not_retrieved` | provisional_variant:human-hot-wheels-silverado-trail-boss-lt-silver-series-performance-trucks, provisional_variant:human-racing-champions-1973-plymouth-cuda-nhra-funny-car-racing-champions-yellow, provisional_variant:human-hot-wheels-mercedes-benz-sprinter-car-culture-premium-deutschland-design, provisional_variant:human-hot-wheels-65-dodge-coronet-premium-car-culture, provisional_variant:human-hot-wheels-honda-civic-eg-premium-fast-furious |
| `fre-positive-440103f8ef3c6b70-lexical` | positive_family / lexical_variation | — | `expected_identity_not_retrieved` | provisional_variant:human-hot-wheels-toyota-off-road-truck-silver-series-silver-series, provisional_variant:human-hot-wheels-2012-mustang-boss-302-laguna-seca-mainline-2012-new-model-black-and-red, provisional_variant:human-hot-wheels-angry-birds-minion-pig-mainline-angry-birds-minion-pig, provisional_variant:human-hot-wheels-tesla-model-s-plaid-mainline-red, provisional_variant:human-m2-1956-ford-f-100-truck-m2-target-exclusive |
| `fre-positive-4d2de6db3d5bba63-lexical` | positive_family / lexical_variation | — | `expected_identity_not_retrieved` | provisional_variant:human-hot-wheels-angry-birds-minion-pig-mainline-angry-birds-minion-pig, provisional_variant:human-hot-wheels-tesla-model-s-plaid-mainline-red, provisional_variant:human-hot-wheels-2012-mustang-boss-302-laguna-seca-mainline-2012-new-model-black-and-red |
| `fre-positive-526b697937fde7cc-lexical` | positive_family / lexical_variation | — | `no_candidates` | — |
| `fre-positive-57cf5c31afbadc57-lexical` | positive_family / lexical_variation | — | `expected_identity_not_retrieved` | provisional_variant:human-hot-wheels-dodge-van-mainline-hw-metro-best-buy-exclusive, review_family:fandom-family-db3fe3a0103099ec, review_family:fandom-family-45af5b93f3f6650f, review_family:fandom-family-fd96307f2dc8b421, provisional_variant:human-hot-wheels-silverado-trail-boss-lt-silver-series-performance-trucks |
| `fre-positive-7e221ec8ecd02815-lexical` | positive_family / lexical_variation | — | `expected_identity_not_retrieved` | provisional_variant:human-auto-world-2020-ford-f-150-lariat-auto-world-red, provisional_variant:human-hot-wheels-subaru-brat-hw-off-road-pearl-yellow-kmart-exclusive |
| `fre-positive-8a07157f2af2ddd5-lexical` | positive_family / lexical_variation | — | `expected_identity_not_retrieved` | provisional_variant:human-auto-world-2020-ford-f-150-lariat-auto-world-red, provisional_variant:human-hot-wheels-subaru-brat-hw-off-road-pearl-yellow-kmart-exclusive |
| `fre-positive-a1b198f7d235f778-lexical` | positive_family / lexical_variation | — | `expected_identity_not_retrieved` | provisional_variant:human-hot-wheels-ford-shelby-gt-500-super-snake-mainline-faster-than-ever, review_family:fandom-family-b3cd4f5a5f7e196a, review_family:fandom-family-db3fe3a0103099ec, review_family:fandom-family-b31d285560d8a242, review_family:fandom-family-aaafff57ac4d4daa |
| `fre-positive-a8e0dec4abdc4131-lexical` | positive_family / lexical_variation | — | `expected_identity_not_retrieved` | review_family:fandom-family-356e4ef63275a661, provisional_variant:human-hot-wheels-1994-amg-mercedes-c-class-dtm-car-culture-premium-deutschland-design, provisional_variant:human-hot-wheels-65-dodge-coronet-premium-car-culture, provisional_variant:human-hot-wheels-fangster-car-hw-city-treasure-hunts, review_family:fandom-family-89930c384be2e8bf |
| `fre-positive-d816204cf649a0c0-lexical` | positive_family / lexical_variation | — | `expected_identity_not_retrieved` | provisional_variant:human-hot-wheels-96-nissan-180sx-type-x-hw-race-team-blue, provisional_variant:human-hot-wheels-65-dodge-coronet-premium-car-culture, provisional_variant:human-hot-wheels-fangster-car-hw-city-treasure-hunts, provisional_variant:human-hot-wheels-shelby-cobra-daytona-coupe-mainline-hw-race-day-gulf, provisional_variant:human-racing-champions-1973-plymouth-cuda-nhra-funny-car-racing-champions-yellow |

## Interpretation boundary

This result measures retrieval over 42 accepted casting-family identities, four merge controls, seven hold controls, and ten unrelated controls. It does not establish release-variant accuracy, canonical matching accuracy, calibration quality, production readiness, or PostgreSQL/pgvector scale performance.

Recorded limitations: `synthetic_challenge_queries_not_live_marketplace_traffic`, `casting_family_retrieval_not_release_variant_resolution`, `small_42_family_domain_with_wide_uncertainty`, `no_postgresql_pgvector_or_production_latency_measurement`, `v1_holdout_becomes_development_known_after_this_report`.

A failed gate is preserved as evidence. Any retriever redesign informed by these errors requires a separately authored v2 holdout before new final-quality claims are made.
