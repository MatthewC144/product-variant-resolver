# AI eval — Human Knowledge rank-1 anchor confidence v4

Date: 2026-09-21. Scope: public development only. Verdict: **FAIL for promotion**.

| Rubric area | Result | Evidence and boundary |
|---|---|---|
| Dataset disclosure | PASS | 10 valid low-coverage anchors, 12 absent-identity negatives, 142-document corpus, and all hashes are committed. |
| Leakage control | PASS | Pack and protocol precede retrieval; source excludes private artifact paths and declares no private reads. |
| Retrieval integrity | PASS | Exactly 22 Top-5 calls; all ten policies reuse the same 42 raw candidates. |
| Existing recall | PASS through 0.61 | 168/168 old positives and 24/24 prior required targets remain; higher settings lose one old positive. |
| New positive recall | PASS through 0.61 | All ten valid low-coverage rank-1 anchors remain; 0.625 and above lose one. |
| Missing-identity safety | FAIL | Best tested setting still returns candidates for 4/12 absent identities; zero was required. |
| Selection integrity | PASS | All settings are ineligible, so the deterministic selector emits no winner. |
| Release safety | PASS | No runtime/API/private-evaluation authorization or canonical effect is produced. |

The evaluation rejects the proposed scalar confidence, not the integrity of the experiment. A
passing automated test suite cannot override the failed product gate. This result therefore blocks
private shadow evaluation and runtime integration.
