# v4 identity-bounded development evaluation

Date: 2026-09-14. Development verdict: PASS; engineering checkpoint: PASS.
Independent final verdict: NOT EVALUATED. Default remains v2; T49 not authorized.

| Rubric dimension | Evidence / verdict |
|---|---|
| Dataset/provenance honesty | Same already-viewed identity-derived 199 dev cases; 142 typed docs; 3,000 synthetic docs/120 probes; immutable protocol/source binding: PASS disclosure, not independent accuracy. |
| Fixed selection and completeness | Exactly 21 configs, 4,179 real plus 2,520 scale raw outputs/work/sample records, no exclusions/tuning; every config qualifies: PASS. |
| Retrieval/ranking | Selected 0.50/1.0: R@5 168/168, R@1 165/168, MRR 0.9911; each style 42/42: PASS development gates only. |
| Safety | Merge 4/4, forbidden 0, unrelated nonempty 0/20; ten noise-only negatives remain counted: PASS development gates. |
| Cost/anti-abstention | Selected p95 real/scale 2.07/45.14 ms; exact/edit/context 60/60,20/20,20/20; raw/subgroup/max-work disclosed: PASS scoped gates. |
| Measurement honesty | Non-isolated arm64/Python3.12.13/10-CPU in-process queries; brief initial test overlap; no sample rerun, original-20 subgroup separate; no production claim: PASS disclosure. |
| Model/corpus claims | hashing-v1 not neural; synthetic numeric cores/wrapper edits not true core-typo test or 3,000 real rows: PASS disclosure. |
| Artifact/runtime failure safety | Full raw report replay/source/policy/limits/winner binding, exclusive publication, no-winner preservation, genuine API SHA/canonical equality: PASS tested scope. |
| Independent final/runtime closure | No new owner-approved final pack/score or fresh container runtime: NOT EVALUATED. |

See [complete evidence](../human-knowledge-identity-development-v1.md), checksum-bound
[raw report](../../../reports/human-knowledge-identity-development-v1/selection.json),
[readable report](../../../reports/human-knowledge-identity-development-v1/selection.md).
329 tests pass, one existing warning. Historical v3 development/v1 final FAILs remain published;
neither is replaced by this new development PASS. Final owner review and all final/closure gates
remain mandatory; no actual catalog promotion/default deployment is implied.
