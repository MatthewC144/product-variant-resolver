# Review-Family Materialization — Lite QA Review

> Date: 2026-09-09
>
> Verdict: **PASS**
>
> Runtime/persistence scope: intentionally unchanged

## Outcome

T46 implements the confirmed specification as a separate review-only family registry. The builder
verifies the final adjudicated queue, the revision-frozen 100-row staging dataset, the existing
human-backed catalog, and all three manifests before producing output. It creates 42 stable
family-only review entities, 4 exact links to existing human-backed families, and 7 non-indexable
hold exclusions. The row split is 79/9/12 and every one of the 100 release references remains held.

The focused suite passes 9/9 and the complete host suite passes 168/168. Fixture validation, the
complete Wiki data chain, all five research and five priority-two decision checkpoints, registry
`--check`, Python compilation, both Compose configurations, and whitespace checks pass.

## Requirement coverage

| Requirement | Result | Evidence |
|---|---|---|
| RFM-R1 | PASS | Builder verifies six frozen input files, declared versions, three manifest checksums, `adjudicated`, and zero pending. Changed queue checksum/status tests fail closed. |
| RFM-R2 | PASS | Only completed create/merge/hold, family-only scope, and variant hold are accepted; widened variant scope fails. |
| RFM-R3 | PASS | Exactly 42 new entities reuse `family_review_id` and derive unique UUIDv5 values from the fixed source namespace. |
| RFM-R4 | PASS | Exactly 4 links resolve to the expected human casting IDs/UUIDs and mint no second family UUID. Unknown targets fail. |
| RFM-R5 | PASS | Exactly 7 named holds retain decision evidence and have `retrieval_eligible=false`. |
| RFM-R6 | PASS | All source rows are held release references; serialized registry contains no `provisional_variants` or `canonical_uuid`. |
| RFM-R7 | PASS | Every new entity has exactly one alias equal to its approved display name; normalized family key is separate. |
| RFM-R8 | PASS | Accepted entities/links retain batch, reviewer, time, reason, evidence, source IDs, revision `790665`, and `CC-BY-SA`. |
| RFM-R9 | PASS | Stable ordered JSON/Markdown regeneration is byte-identical and contains no build timestamp. |
| RFM-R10 | PASS | Frozen manifest proves 42/4/7 families, 79/9/12 rows, 100 held references, and all four promotion/index/persistence counts at zero. |
| RFM-R11 | PASS | Tests reject checksum drift, partial state, widened scope, duplicate rows, unknown targets, and accepted-name collisions before output. |
| RFM-R12 | PASS | No canonical/human runtime catalog, API, service, migration, evaluation, calibration, or PostgreSQL file changed. |
| RFM-R13 | PASS | `--check` compares all three artifacts byte for byte and a hash-before/hash-after test proves it performs no writes. |

## Findings

### Blocker

None.

### Important limitations

1. The new entities are review identities, not canonical products or reviewed release variants.
2. The registry is deliberately excluded from current Dual-RAG retrieval; runtime behavior is
   unchanged until a separately specified family-document integration is implemented.
3. UUID stability depends on preserving the documented namespace string and immutable source
   family-review ID.
4. Atomic output preparation prevents validation failures from overwriting accepted files, but a
   general filesystem/power failure during the final sequence is not a multi-file transaction.
5. Text-source evidence can still contain upstream errors and does not replace physical-tool
   verification.

## Carry forward

T47 should specify family-level documents for the human-knowledge source, including debug schema,
ranking scope, hold exclusion, and the rule that a family suggestion can never populate canonical
response identity. T48 must evaluate that enlarged source on an independently written casting-
grouped holdout before T49 PostgreSQL materialization or larger yearly-list ingestion.
