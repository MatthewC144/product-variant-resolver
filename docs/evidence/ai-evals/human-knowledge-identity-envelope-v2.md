# AI eval — Human Knowledge query-global identity envelope v2

Date: 2026-09-22. Scope: public historical development. Verdict: **FAIL for promotion**.

| Rubric area | Result | Evidence and boundary |
|---|---|---|
| Dataset disclosure | PASS | Exact public denominators are 223 existing, 22 v4, and 24 HIC-v1 rows; all source hashes are manifest-bound. |
| Leakage control | PASS | No private path, query, label, candidate, rank, or result is read; private-local reads are false. |
| Retrieval integrity | PASS | Historical rescoring executes zero retrieval; the proposed 32 new calls never occur. |
| Evidence auditability | PASS | Every candidate decision exposes one query-global envelope, identity form, alignment, numeric state, residuals, reason codes, and outcome. |
| Numeric conservation | PASS | `88`/`1988` uses one structural rule; incompatible `R33`/`R34`, `R33`/`BNR34`, and `M2`/`M4` remain conflicts. |
| Existing regression | FAIL | The best safety-oriented policy retains only 146/168 existing positives; 168/168 is required. |
| V4 positive preservation | FAIL | The closest safety policy retains 9/10; 10/10 is required. |
| HIC-v1 positive preservation | FAIL | The closest safety policy retains 10/12; 12/12 is required. |
| Absent-identity safety | FAIL | The closest policy still leaves 1/12 nonempty in both negative sets; zero is required. |
| Selection integrity | PASS | Zero policies are eligible; the deterministic verdict is `winner: null`. |
| Release safety | PASS | No protocol, holdout, raw retrieval, private evaluation, runtime/API/database/canonical/variant authorization exists. |

The AI-related behavior is deterministic candidate admission rather than generated prose. Passing
unit and repository tests proves implementation consistency, not retrieval-policy quality. The
pre-holdout historical gate correctly stops an unsafe method before spending 32 new retrieval calls.

The experiment's approximately 10x auditability advantage over an opaque cross-encoder remains:
every false admission and lost positive can be traced to explicit envelope and rule states. That
auditability also makes the failure unambiguous. Promotion remains blocked, and any v3 attempt must
use a new specification rather than tuning this frozen result.
