# Human Knowledge identity-contradiction development v1 — evidence

Date: 2026-09-21. Lite / Lean Industrial. Verdict: **experiment valid; no policy qualified**.

## Frozen inputs and collection

The public pack was frozen before retrieval with twelve positive-preservation cases and twelve
corpus-absent identity contradictions. The positives span twelve public knowledge documents and do
not reuse the ten v4 anchor-positive cases. Four positive challenge styles and four negative
challenge styles each contain three cases.

| Artifact | SHA-256 |
|---|---|
| Development source | `167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f` |
| Pack | `e86bb87f5c37b951482a782af09742617bc1820fe4bca3faacf122beb0f8e08c` |
| Pack manifest | `fe4cab04f3e45142f3d5160e5405d94fe5cbddfd2c75b34493b6a5e507f6ae9f` |
| Protocol | `eeb30a56e0207dad41e7fa5a6889cef9a8377c05250f31508431e836946a6818` |
| Protocol manifest | `e6c5c262525868b4917e8bf6efd0c0b37c797fa4c9d3e3ebfe23f88a0f45ad0e` |
| Raw retrieval | `3ea4a12f36e671b2acfd5d0b7e2ad1cc9ac4705a8b6ad796f7e18dd3a3301995` |
| Raw manifest | `2c895516c071f14cca778ec7e5ee87249925f606977203e35a28c60ca1c5bc01` |
| Selection JSON | `3f72ab6e3e33d92b1f8fdef2b7872fec0ac7a6835da6609e39f34715ecb51589` |
| Selection Markdown | `9322b6ffbe4b8a62ffaea3ebb277a8cdb539c112814f7caddf1b116fbde9f637` |

One collection pass made exactly 24 Top-5 calls and produced 24 ordered rows with 42 total
candidates and zero retrieval errors. Raw rows contain query, candidate, rank, retrieval work, and
error fields, but no expected or label key. The manifest records `expected_labels_present: false`
and `private_local_artifacts_read: false`. Repeating collection returns `unchanged` before reaching
the retriever.

## Measured policy results

All seven policies reuse the same raw bytes and rescore the existing 223 public rows plus the frozen
v4 22 rows without retrieval.

| Policy | Eligible | Existing positives | V4 positives | V4 absent nonempty | New positives | New absent nonempty |
|---|---:|---:|---:|---:|---:|---:|
| `baseline-anchor` | no | 168/168 | 10/10 | 11/12 | 12/12 | 10/12 |
| `numeric-only` | no | 167/168 | 10/10 | 10/12 | 12/12 | 10/12 |
| `contradiction-050` | no | 164/168 | 9/10 | 1/12 | 11/12 | 1/12 |
| `contradiction-075` | no | 165/168 | 9/10 | 1/12 | 11/12 | 2/12 |
| `contradiction-100` | no | 167/168 | 10/10 | 6/12 | 12/12 | 5/12 |
| `contradiction-125` | no | 167/168 | 10/10 | 6/12 | 12/12 | 5/12 |
| `contradiction-150` | no | 167/168 | 10/10 | 7/12 | 12/12 | 5/12 |

Every policy has zero contradiction-computation errors. The strict thresholds greatly improve
negative rejection but reject valid positive evidence first; the looser thresholds preserve the new
positive cases but leave unsafe absent identities and lose one existing positive. The predeclared
selector therefore returns `winner: null`.

## Verification and boundary

The installed non-editable wheel exposes all five CLI phases. Two consecutive installed
`pvr-develop-human-knowledge-identity-contradiction --check` calls independently recomputed the
selection and returned `valid` with a null winner. Eighteen focused, 52 related, and 788 complete
repository tests pass; Ruff/format, MyPy, compileall, and artifact integrity pass. The only warning
is the existing Starlette/AnyIO deprecation warning.

No private query, label, candidate, rank, result, or path was used. No private evaluation, API,
Dual RAG runtime, PostgreSQL, canonical catalog, release promotion, color, wheel, tampo, edition, or
packaging behavior is authorized or changed.
