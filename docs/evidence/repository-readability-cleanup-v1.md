# Repository Readability Cleanup v1 — Evidence

Date: 2026-10-11  
Verdict: **PASS**

## Outcome

The repository now exposes three reading depths:

```text
README landing page
    → docs technical index / architecture / code tour / results
        → immutable evidence, specs, reports, and historical chronology
```

The 367-line research-heavy README became a 194-line portfolio landing page. The public headline is
now product entity resolution and learning-to-rank, with one primary ranking result: exact-release
Top-1 `55% → 64%` on 100 paired source observations from 50 held-out identities. Historical
single-source, saturated-fixture, domain adaptation, calibration, and ONNX results remain available
in `docs/RESULTS.md` but no longer compete for the first-read narrative.

## Added navigation

- `docs/README.md`: technical index.
- `docs/architecture/system-overview.md`: Mermaid architecture and component rationale.
- `docs/CODE-TOUR.md`: seven-file implementation path.
- `docs/RESULTS.md`: current/historical/negative result hierarchy.
- `docs/LIMITATIONS.md`: single human-readable limitation source.
- `docs/ARTIFACT-POLICY.md`: retention classes and large-artifact inventory.
- `docs/archive/README.md`: entry to immutable historical evidence without mass-moving it.

## Claim consistency

The new test reads
`data/evaluation/serper-dual-source-evaluation-v1/raw-pointwise-final-test.json` and verifies the
README values `55%`, `64%`, `86%`, `95%`, `0.722`, `0.792`, and `99%`. It also verifies the paired
denominator, required entry points, public terminology, and every local Markdown link in the curated
reading path.

## Active-core quality

Ruff passes for the six active runtime modules and changed compatibility/tests. Strict MyPy passes
for `retrieval.py`, `rerank.py`, `calibration.py`, `policy.py`, `service.py`, and `api.py`.

The type-only `service.py` change required a new exact hash in the existing storage-wrapper
compatibility allowlist. `retrieval.py` was restored to its historical compatible hash
`2ef9737d319b7d3ca6bdfd540e58147365eba4e2b6b4d47f1484fab3025f06c1`; current API parity and
historical compatibility tests pass.

## Verification record

- Focused pytest: 83 passed.
- Ruff: zero findings in the active/changed scope.
- Strict MyPy: zero issues in six active-core files.
- README line target: 194 / 150–250.
- Documentation links: all curated local targets resolve.
- Public Dual-RAG headline wording: absent from README and Portfolio Guide.
- Secret audit and `git diff --check`: pass.

## Non-actions

No model was trained or selected. No holdout was opened. No frozen metric, dataset membership,
canonical record, score, threshold, policy, or FastAPI default changed. Large artifacts were
inventoried but not deleted or migrated.

