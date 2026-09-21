# AI eval — Human Knowledge identity contradiction v1

Date: 2026-09-21. Scope: public development only. Verdict: **FAIL for promotion**.

| Rubric area | Result | Evidence and boundary |
|---|---|---|
| Dataset disclosure | PASS | Frozen 12-positive/12-negative pack, challenge distribution, 142-document public corpus, and artifact hashes are committed. |
| Leakage control | PASS | Pack and protocol precede retrieval; raw rows contain no expected/label key; private reads are false. |
| Retrieval integrity | PASS | Exactly 24 Top-5 calls produced 24 rows and 42 candidates; seven policies reuse identical bytes. |
| Evidence auditability | PASS | Each decision records query span, ordered alignment, residual atoms, numeric state, reason codes, and admit/abstain outcome. |
| Existing regression | FAIL for candidate policies | Baseline is 168/168; every contradiction policy loses one to four existing positives. |
| V4 positive recall | PASS only for numeric/1.00+ | The strict 0.50/0.75 policies retain 9/10 rather than the required 10/10. |
| New positive recall | PASS only for baseline/numeric/1.00+ | The strict 0.50/0.75 policies retain 11/12 rather than 12/12. |
| Absent-identity safety | FAIL | The best strict policy still leaves 1/12 nonempty in both negative sets; zero is required. |
| Selection integrity | PASS | No policy meets every exact gate, so deterministic selection emits `winner: null`. |
| Release safety | PASS | No private evaluation or runtime/API/database/canonical/variant authorization is produced. |

The AI-related artifact is an admission decision over retrieval candidates, not a generated natural
language answer. Its quality rubric therefore focuses on evidence leakage, deterministic
recomputation, positive preservation, absent-identity rejection, and fail-closed selection.

The experiment successfully demonstrates an auditable candidate-specific signal, but it does not
demonstrate a deployable policy. Automated test success proves implementation integrity; it cannot
override the failed recall and safety gates. Promotion remains blocked.
