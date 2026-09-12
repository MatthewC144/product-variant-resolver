# Human Knowledge Retriever Redesign — Tasks

> Mode: Lite / Lean Industrial
>
> Status: In progress; HRR-T1 complete

## Task order

### HRR-T1 — Freeze the development-only challenge contract `[backend/qa]`

- [x] Implement strict 199-case development builder/manifest validation. _(→HRR-R1–R3)_
- [x] Author four declared transformations for every family plus all controls, then freeze before
  running candidate configurations. _(→HRR-R2–R3)_

Files:

- `scripts/build_family_retrieval_development.py`
- `data/evaluation/family-retrieval-development-v1/`
- `tests/test_family_retrieval_development.py`
- `docs/evidence/family-retrieval-development-v1.md`

Acceptance:

- Exact 199/168/4/7/20 counts, 42×4 positive coverage, disclosure, non-v1 equality, deterministic
  bytes, and atomic invalid-input preservation pass.
- No retriever output or configuration result exists before the development pack is committed.

### HRR-T2 — Implement the experimental v3 character-hybrid path `[backend/frontend]`

- [ ] Add allowlisted character identity texts, TF-IDF posting retrieval, union eligibility, and
  three-source weighted RRF behind an experimental v3 configuration. _(→HRR-R4–R8)_
- [ ] Extend typed debug/API/UI evidence and failure/version metadata without changing canonical
  authority. _(→HRR-R11–R14)_

Files:

- `src/product_variant_resolver/human_knowledge.py`
- `src/product_variant_resolver/schemas.py`
- `src/product_variant_resolver/service.py`
- `src/product_variant_resolver/config.py`
- `ui/app.js`
- `tests/unit/test_human_knowledge.py`
- `tests/integration/test_catalog_service.py`
- `tests/api/test_api.py`
- `tests/ui/test_debug_ui.py`

Acceptance:

- Character-only misspellings can enter the bounded union, missing source ranks fuse correctly,
  scores/ties are deterministic, and invalid artifacts fail readiness.
- Canonical output and debug-off response shapes remain byte/field compatible.

### HRR-T3 — Select and freeze v3 using development data only `[backend/qa]`

- [ ] Evaluate exactly the precommitted 21 configurations and write all raw candidate results,
  safety failures, metrics, and deterministic selection outcome. _(→HRR-R8–R10)_
- [ ] If and only if a candidate qualifies, freeze its versioned runtime artifact and code/corpus/
  development hashes; otherwise publish FAIL and stop. _(→HRR-R10–R11)_
- [ ] Measure disclosed 142-document and synthetic 3,000-document local cost. _(→HRR-R15)_

Files:

- `src/product_variant_resolver/human_knowledge_selection.py`
- `scripts/generate_human_knowledge_selection_report.py`
- `scripts/freeze_human_knowledge_v3.py`
- `artifacts/human-knowledge-retrieval-v3.json`
- `reports/family-retrieval-development-v1/`
- `tests/evaluation/test_human_knowledge_selection.py`
- `docs/evidence/ai-evals/human-knowledge-retrieval-development-v1.md`

Acceptance:

- V1 benchmark/report files are never loaded by selection code.
- No-winner output cannot create or overwrite the active v3 artifact.
- A winner is reproducible from raw results and meets every safety/quality/cost constraint.

### HRR-T4 — Freeze a new output-blind v2 final query pack `[qa/doc_curator]`

- [ ] Commit the selected v3 implementation/artifact freeze before query authoring begins.
  _(→HRR-R11,HRR-R16)_
- [ ] Author and freeze 105 new v2 test questions without viewing v3 output, rejecting any reused
  v1/development/indexed query. _(→HRR-R16–R17)_
- [ ] Present every query/reference pair and checksum for project-owner confirmation; stop before
  labels or retrieval. _(→HRR-R17)_

Files:

- `scripts/author_family_retrieval_query_pack_v2.py`
- `data/evaluation/family-retrieval-v2/query-pack.json`
- `data/evaluation/family-retrieval-v2/query-pack-manifest.json`
- `tests/test_family_retrieval_benchmark_v2.py`
- `docs/evidence/family-retrieval-query-pack-v2.md`

Acceptance:

- Git history proves v3 code/artifact freeze precedes v2 queries.
- All 105 queries are output-blind, complete, distinct from prohibited sources, and owner-readable.

### HRR-T5 — Record owner labels and run one final v2 evaluation `[qa]`

- [ ] Record attributable decisions for every unchanged v2 query and freeze the benchmark.
  _(→HRR-R17)_
- [ ] Retrieve before label access, generate raw JSON/Markdown, apply unchanged final gates, and
  preserve PASS or FAIL without tuning. _(→HRR-R18–R19)_

Files:

- `data/evaluation/family-retrieval-v2/owner-decisions.json`
- `data/evaluation/family-retrieval-v2/benchmark.json`
- `data/evaluation/family-retrieval-v2/benchmark-manifest.json`
- `reports/family-retrieval-v2/`
- `docs/evidence/ai-evals/family-retrieval-holdout-v2.md`

Acceptance:

- All metrics/gates recompute from ordered candidates and exact frozen inputs.
- No final evaluation occurs before explicit project-owner label confirmation.

### HRR-T6 — Close the Lite redesign gate and decide T49 `[qa/doc_curator]`

- [ ] Run complete tests/data chain, canonical and T47/T48 regressions, development/final report
  checks, compilation, API/UI, Compose, scope, and disclosed cost checks. _(→HRR-R12–R20)_
- [ ] Map every requirement, update AI-eval/project log/README/decision record, and authorize T49
  only on a complete v2 PASS. _(→HRR-R18–R20)_

Files:

- `specs/human-knowledge-retriever-redesign/review.md`
- `docs/evidence/human-knowledge-retriever-redesign.md`
- `docs/PROJECT-LOG.md`
- `docs/decisions/product-variant-resolver.md`
- `README.md`

Acceptance:

- Engineering and model-quality verdicts are separate, complete, and evidence-backed.
- A failed development/final gate leaves T49 explicitly blocked.

## Requirement traceability

| Requirement | Implemented/verified by |
|---|---|
| HRR-R1 | T1/T3/T4 validators and scope tests |
| HRR-R2 | T1 development builder and count tests |
| HRR-R3 | T1 manifest/disclosure tests |
| HRR-R4 | T2 typed identity field allowlists |
| HRR-R5 | T2 character index unit tests |
| HRR-R6 | T2 character-only and no-evidence tests |
| HRR-R7 | T2 union/fusion tests |
| HRR-R8 | T1/T3 frozen grid and execution checks |
| HRR-R9 | T3 selection-rule tests and raw report |
| HRR-R10 | T3 no-winner negative path |
| HRR-R11 | T3 artifact/hash/version checks |
| HRR-R12 | T2 API/UI/health tests |
| HRR-R13 | T2/T6 canonical regression |
| HRR-R14 | T2/T3 safety/failure tests |
| HRR-R15 | T3 cost report and scope disclosure |
| HRR-R16 | T3/T4 commit-order/source-freeze checks |
| HRR-R17 | T4/T5 final pack and approval validators |
| HRR-R18 | T5 immutable final gate |
| HRR-R19 | T5/T6 FAIL/evidence behavior |
| HRR-R20 | T6 final review and decision record |

## Dependency order

```text
owner confirms spec
       │
       ▼
HRR-T1 dev pack freeze → HRR-T2 experimental v3 → HRR-T3 dev selection
                                                       │
                                  no winner ────────────┴──► stop/redesign
                                                       │ winner + commit
                                                       ▼
                                 HRR-T4 v2 query freeze → owner confirms labels
                                                                      │
                                                                      ▼
                                                    HRR-T5 one final evaluation
                                                                      │
                                                                      ▼
                                                        HRR-T6 closure/T49 decision
```

No implementation begins until the project owner confirms these three specification files. No v3
candidate output is permitted during T4 authoring, and T5 cannot run before the owner confirms the
frozen v2 query/reference pack.
