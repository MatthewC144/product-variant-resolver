# AI eval — Human Knowledge identity-certificate set v4

Date: 2026-09-24. Scope: public historical development. Verdict: **FAIL for promotion**.

| Rubric area | Result | Evidence and boundary |
|---|---|---|
| Grounding | PASS | Certificates use normalized public primary-casting claims; aliases can only bridge to those claims. No generated/free-form assertion creates identity. |
| Public/private separation | PASS | The manifest records `private_local_artifacts_read: false`; no private query, label, candidate, rank, result, owner row, or projection document is read or named. |
| Leakage control | PASS | Series, color, wheel, tampo, edition, packaging, release metadata, price, provenance, case IDs, expected labels, UUID ordering, and private outcomes are excluded from decisions. |
| Certificate integrity | PASS | 142 documents map once to 139 authorities; 460 claims produce 401 minimal certificates with elimination/deletion proofs; seven unresolved authorities remain ineligible. |
| Candidate independence | PASS | Query support is built before candidates and reused by checksum across ranks; candidate rank/score/UUID cannot change the support set. |
| Retrieval integrity | PASS | Historical rescoring executes zero retrieval; the conditional 32 holdout calls never occur. |
| Evidence integrity | PASS | Source, prior experiments, corpus, rows, inventory, report, and manifest are hash-bound; measured artifact regressions reject drift. |
| Explainability | PASS | Evidence exposes claims, eliminated competitors, bridges, support/ambiguity, context, unresolved atoms, frame conflicts, membership, reasons, rank, and final decision. |
| Positive preservation | FAIL | Exact/structural/bounded preserve only 42/82/137 of 168 existing positives and fail other required positive gates. |
| Negative safety | PASS | All three certificate profiles produce 0/12 output on each absent-identity set and preserve both secondary BNR34 vetoes. |
| Selection integrity | PASS | Zero profiles are eligible; the deterministic result is `winner: null`, not a closest-profile promotion. |
| Release safety | PASS | No protocol, holdout, private evaluation, API, Dual RAG, PostgreSQL, canonical, release, variant, or physical-feature authorization exists. |

The evaluated AI behavior is structured retrieval admission rather than generated prose. Green
software tests prove deterministic implementation and evidence integrity, not product eligibility.
The exact gates correctly reject a safe but overly restrictive profile before another 32 retrieval
calls or a private evaluation are spent.

V4 remains substantially more auditable than an opaque learned admission model: every minimal
claim, eliminated authority, alias bridge, context decision, conflict, and membership decision can
be recomputed from committed public evidence. That auditability makes the recall failure explicit;
it does not make the profile eligible. V4 is the final identity-admission attempt in this roadmap.
The next experiment must compare No Reranker/RRF, Neural Pointwise, and Listwise on a separately
specified frozen candidate pool rather than retuning these certificates after observing failure.
