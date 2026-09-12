# Family Retrieval Evaluation — Tasks

> Mode: Lite / Lean Industrial
>
> Status: Confirmed; T48.1–T48.4 complete, T48.5 next

## Task order

### T48.1 — Implement the frozen benchmark contract `[backend]`

- [x] Build strict query-pack, owner-decision, benchmark, and manifest validators. _(→FRE-R1–R9,FRE-R15)_
- [x] Add deterministic build/`--check`, atomic replacement, and negative tests. _(→FRE-R8,FRE-R16)_

Files:

- `scripts/build_family_retrieval_benchmark.py`
- `tests/test_family_retrieval_benchmark.py`
- `data/evaluation/family-retrieval-v1/`

Acceptance:

- Invalid or incomplete inputs cannot produce or overwrite a benchmark.
- The contract enforces exact counts, authoring declarations, owner approval, leakage rules,
  test-only use, system-under-test versions, and all excluded uses.

### T48.2 — Author and freeze the output-blind query pack `[doc_curator/qa]`

- [x] Write exactly 84 two-style positive cases across all 42 accepted families. _(→FRE-R2–R5)_
- [x] Add 4 merge, 7 hold, and 10 unrelated controls without viewing retrieval output. _(→FRE-R3,FRE-R6)_
- [x] Freeze the proposed query pack and authorship manifest before scoring. _(→FRE-R1–R3,FRE-R8–R9)_

Files:

- `data/evaluation/family-retrieval-v1/query-pack.json`
- `data/evaluation/family-retrieval-v1/query-pack-manifest.json`
- `scripts/author_family_retrieval_query_pack.py`
- `docs/evidence/family-retrieval-query-pack-t48.md`

Acceptance:

- All queries pass structural/non-copying checks and no retrieval result is generated in this task.
- The four single-token families have explicit lexical-variation challenges.

### T48.3 — Record and validate project-owner labels `[qa/doc_curator]`

- [x] Present the frozen cases for project-owner confirmation without retriever ranks/scores. _(→FRE-R7)_
- [x] Store attributable decisions for all 105 cases and build the frozen benchmark. _(→FRE-R7–R9)_

Files:

- `data/evaluation/family-retrieval-v1/owner-decisions.json`
- `data/evaluation/family-retrieval-v1/benchmark.json`
- `data/evaluation/family-retrieval-v1/benchmark-manifest.json`
- `scripts/record_family_retrieval_owner_decisions.py`
- `tests/test_family_retrieval_benchmark.py`

Acceptance:

- Query-pack checksum precedes and is bound by the owner-decision file.
- No pending/partial/changed decision can become scoring-eligible.

### T48.4 — Evaluate the frozen Human Knowledge RAG v2 `[backend/qa]`

- [x] Implement read-only per-case scoring, metrics, gates, and error categories. _(→FRE-R10–R13)_
- [x] Generate deterministic JSON/Markdown reports and an AI-eval record. _(→FRE-R11–R14)_

Files:

- `src/product_variant_resolver/human_knowledge_evaluation.py`
- `scripts/generate_family_retrieval_report.py`
- `tests/evaluation/test_human_knowledge_evaluation.py`
- `reports/family-retrieval-v1/`
- `docs/evidence/ai-evals/family-retrieval-holdout-v1.md`

Acceptance:

- Every aggregate is recomputable from ordered per-case raw results.
- A valid failed gate produces an explicit FAIL report and never triggers same-set tuning.

### T48.5 — Close the Lite evaluation gate `[qa/doc_curator]`

- [ ] Run focused/full tests, deterministic data chain, canonical regression, compilation, Compose,
  and scope checks. _(→FRE-R15–R16)_
- [ ] Map all requirements, record limitations, and decide whether T49 may begin. _(→FRE-R12–R16)_

Files:

- `specs/family-retrieval-evaluation/review.md`
- `docs/evidence/family-retrieval-evaluation-t48.md`
- `docs/PROJECT-LOG.md`
- `README.md`

Acceptance:

- PASS/FAIL is determined only by precommitted gates, not rewritten after seeing results.
- Documentation distinguishes debug retrieval quality from canonical and production accuracy.

## Requirement traceability

| Requirement | Implemented/verified by |
|---|---|
| FRE-R1 | T48.1 system-under-test freeze and T48.2 pre-score manifest |
| FRE-R2 | T48.1 authoring validator and T48.2 source pack |
| FRE-R3 | T48.1 exact composition validator and T48.2 cases |
| FRE-R4 | T48.1 coverage validator and T48.2 positive cases |
| FRE-R5 | T48.1 leakage/non-triviality tests and T48.2 challenges |
| FRE-R6 | T48.1 control validators and T48.2 controls |
| FRE-R7 | T48.3 owner decision artifact and negative tests |
| FRE-R8 | T48.1/T48.3 deterministic manifests and checksums |
| FRE-R9 | T48.1/T48.3 test-only and group-isolation validation |
| FRE-R10 | T48.4 evaluator isolation tests |
| FRE-R11 | T48.4 raw results, metrics, and error tests |
| FRE-R12 | T48.4 precommitted gate tests |
| FRE-R13 | T48.4 FAIL/no-tuning behavior |
| FRE-R14 | T48.4 reports and AI-eval record |
| FRE-R15 | T48.5 repository/persistence/privacy review |
| FRE-R16 | T48.5 complete regression and reproducibility chain |

## Dependency order

```text
T48.1 → T48.2 → project-owner confirmation → T48.3 → T48.4 → T48.5
```

No retrieval run is permitted during T48.2. T48.3 cannot begin until the user has seen and confirmed
the frozen query pack; T48.4 cannot begin until all owner decisions validate.
