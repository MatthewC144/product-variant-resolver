# AI artifact evaluation — Canonical Catalog Application v1

Date: 2026-09-30  
Scope: generated CAR-T4A catalog application artifacts and their public claims only  
Verdict: **PASS — SCOPED CATALOG-APPLICATION CLAIMS ONLY**

This rubric does not score resolver quality, retrieval, ranking or product truth. It evaluates whether the
generated catalog application artifacts say only what their frozen parents and owner-authorized scope support.

| Criterion | Result | Evidence and boundary |
|---|---|---|
| Grounding | PASS | Exactly 20 previously reviewed proposals are mapped into 20 appended rows; the 120-row parent, packet order and proposal bindings remain frozen. |
| Authorization scope | PASS | A separate catalog-application owner Gate exists; exact response stays in the ignored private event. The public claim is catalog application only. |
| Non-invention | PASS | `color=null` and `edition=null` for all 20 rows. Identity uses approved `release_key` plus typed toy identifier, not inferred physical attributes, aliases or rarity. |
| Lineage and integrity | PASS | First run `created`, read-only check `valid`, identical replay `unchanged`; child catalog, data manifest and public application-manifest hashes are recorded. |
| Privacy and publication | PASS | Public artifacts expose aggregate counts, licensing, lineage and hashes, not owner verbatim or private candidate/review payloads. |
| Runtime compatibility | PASS | Final post-apply QA verified the catalog-v2 loader, `ResolverService`, in-memory ingestion and the 26-test PostgreSQL repository／migration／runtime contract subset. |
| Authority honesty | PASS | Public state remains `exact_authority_count=0` and `rhb_t5_authorized=false`; catalog inclusion is not relabeled as manufacturer truth. |

## Allowed claims

- A separately authorized catalog-only batch applied 20 reviewed proposals.
- Current catalog-v2 contains 140 products: 120 synthetic fixture rows and 20 community-snapshot rows.
- All 20 new rows retain null color and edition and are distinguished by approved release identity fields.
- Application artifacts are deterministic and currently report `created` / `valid` / replay `unchanged`.

## Prohibited claims

- The 20 rows are Mattel-verified, manufacturer-certified or official exact truth.
- Catalog application created 20 `approved_exact` authority rows.
- The enlarged catalog makes RHB-T5 authorized or makes the benchmark representative／production-ready.
- The application proves resolver accuracy, improves ranking metrics or validates unseen product variants.

## Evidence status

Final independent post-apply QA verified real application `--check=valid`, temporary replay
`unchanged`, the exact three documented hashes, clean transaction state, 140=120+20 ordering and all
20 null color／edition boundaries. Runtime loader, `ResolverService` and in-memory ingestion passed;
the standalone PostgreSQL repository／migration／runtime contract subset was `26 passed`.

Overall verification recorded focused `201 passed`, full `1245 passed, 1 warning`, and post-Ruff affected
tests `21 passed`. Ruff／format covered 17 files; strict MyPy covered 8 implementation／script files.
Compileall, historical CAR／Fandom／RHB／release／human-alignment checks, JSON／hash, privacy／secret,
license, symlink and diff checks passed or remained byte-identical. The warning is the existing
Starlette／AnyIO deprecation warning.

The post-apply cycle also corrected fixture test-state coupling by reconstructing the immutable 120-row
parent instead of treating the current 140-row child as historical input, and cleaned nine scoped Ruff
issues. Verdict **PASS** applies only to the generated catalog-application artifacts and their bounded
claims. Exact/manufacturer truth, resolver accuracy and benchmark readiness remain not evaluated and
must not be inferred.
