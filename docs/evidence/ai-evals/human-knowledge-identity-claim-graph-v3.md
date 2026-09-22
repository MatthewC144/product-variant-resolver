# AI eval — Human Knowledge identity-claim graph v3

Date: 2026-09-22. Scope: public historical development. Verdict: **FAIL for promotion**.

| Rubric area | Result | Evidence and boundary |
|---|---|---|
| Grounding | PASS | Every decision is grounded in normalized query claims and committed casting/approved aliases; no free-form generated assertion is accepted. |
| Public/private separation | PASS | The manifest records `private_local_artifacts_read: false`; no private query, label, candidate, rank, or result is read or named. |
| Leakage control | PASS | Expected labels, case-specific rules, release metadata, color, series, provenance IDs, and private outcomes are excluded from decision evidence. |
| Retrieval integrity | PASS | Historical rescoring executes zero retrieval; the proposed 32 holdout calls never occur. |
| Evidence integrity | PASS | Source and upstream bytes are SHA-bound; repeated freeze is unchanged and `--check` recomputes the graph, evidence, gates, and null verdict. |
| Explainability | PASS | Candidate output exposes the immutable graph/checksum, local frames, alignments, context decisions, equivalences, residuals, conflicts, rank rule, reasons, and decision. |
| Positive preservation | FAIL | No non-reference policy reaches 168/168 existing, 10/10 v4, 12/12 HIC, and 24/24 prior required targets together. |
| Negative safety | FAIL | The recall-preserving policies leave 11/12 v4 and 10/12 HIC absent identities nonempty and miss both BNR34 vetoes. |
| Safe-policy recall | FAIL | The policies reaching 0/12 on both negative sets retain only 129–134/168 existing, 3–4/10 v4, and 8/12 HIC positives. |
| Selection integrity | PASS | Zero policies are eligible; the deterministic result is `winner: null`, not a best-effort promotion. |
| Release boundary | PASS | No holdout, private evaluation, API, Dual RAG, PostgreSQL, canonical, release, or physical-feature authorization exists. |

The evaluated AI behavior is structured retrieval admission rather than generated prose. Green
software tests prove deterministic implementation, not policy quality. The exact product gates
correctly reject both unsafe high-recall behavior and overly restrictive safe behavior before
another 32 retrieval calls are spent.

The approach remains substantially more auditable than an opaque learned reranker because every
atom role, frame relation, equivalence, conflict, and decision can be recomputed from committed
evidence. That auditability makes the null result clear rather than making the model eligible.
Promotion remains blocked; a future attempt requires a new versioned experiment instead of tuning
the frozen v3 result after observing failures.
