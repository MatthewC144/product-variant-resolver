# AI artifact evaluation — CAR-T5F completion

Date: 2026-10-04
Scope: frozen authority bundle, manifest and CAR-T5F completion claims
Verdict: **PASS — BUNDLE CLAIMS ARE HASH-BOUND, PRIVATE AND GATE-LIMITED**

| Criterion | Result | Evidence and boundary |
|---|---|---|
| Grounding | PASS | Each of 20 records binds one latest exact event and six snapshot-supported evidence hashes. |
| Distinctness | PASS | Twenty canonical UUIDs and family/release identities are distinct; seven families qualify. |
| Authorization | PASS | A fresh CAR-T5F response is privately retained and differs in scope from T5-G1/T5-G2. |
| Privacy | PASS | Public bundle/manifest exclude verbatim owner text and bind only an irreversible authorization hash. |
| Determinism | PASS | Materialization returned `created`; two real replays returned `unchanged`. |
| Composition honesty | PASS | Manifest recomputes 20 variants, seven qualifying families and zero shortfalls. |
| Gate honesty | PASS | Eligibility is only for a fresh RHB-T4 re-audit; CAR-T6 and RHB-T5 remain false. |
| Regression | PASS | Post-materialization full regression passed 1,372 tests; privacy scan found zero private-response leaks. |

## Allowed claims

- CAR-T5F produced a 20-record, seven-family community-snapshot-relative authority bundle.
- The bundle and manifest are deterministic, hash-bound and owner-authorized.
- The bundle is technically eligible to be presented to a new RHB-T4 re-audit.

## Prohibited claims

- The records are manufacturer-certified truth.
- CAR-T5F itself is an RHB-T4 PASS or benchmark-readiness proof.
- CAR-T6 or RHB-T5 is authorized.
- The bundle measures resolver accuracy, listwise/pointwise quality, RAG quality or embedding quality.
- Public Git contains the owner response or private identity.

This PASS covers the CAR-T5F data freeze and the faithfulness of its public claims. CAR-T6, CAR-T7
and RHB-T5 remain separate, unexecuted Gates.
