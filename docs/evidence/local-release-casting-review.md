# Local release casting review queue — verification evidence

Date: 2026-09-17. Lite / Lean Industrial. Current gate: **PASS**.

The offline review builder transformed the validated 1,763-row staging snapshot into 676 normalized
review clusters. It preserves 678 raw casting labels inside the private queue, including two groups
where punctuation or accent folding collapses distinct source spellings. Queue SHA-256 is
`7961d4e6b59623277c3172e24066686e3a6ee01585fac4205a4e4f7254e0b883`.

## Aggregate result

| Candidate class | Review clusters | Source observations |
|---|---:|---:|
| Exact in synthetic fixture and human draft | 1 | 1 |
| Exact in synthetic fixture only | 2 | 8 |
| Exact in human draft only | 40 | 126 |
| No exact candidate | 633 | 1,628 |
| **Total** | **676** | **1,763** |

All 676 clusters remain unresolved. Approved links, canonical promotions, reviewed colors, network
requests, SQL writes, and Dual RAG changes are zero. The complete queue is stored only under the
gitignored local data tree. The committed manifest freezes the source snapshot, catalog inputs, and
private queue hashes while revealing no source row, casting label, candidate ID, or toy number.

## Verification

Eleven focused tests cover every candidate class, multiple fixture variants within one family,
normalization collisions, deterministic input reordering, authority-field rejection, public-output
privacy, current owner-data aggregates, and the committed manifest contract. The full repository
suite passes 640/640. Changed-file Ruff F/I and formatting, strict MyPy for the new module, compileall,
the deterministic CLI `--check`, and `git diff --check` pass. Pytest reports only the existing
Starlette/AnyIO deprecation warning.

This evidence verifies queue mechanics and review boundaries. It does not verify that any observed
label names a real-world casting, that two spelling variants are the same identity, that a catalog
candidate is correct, or that a release variant/color is known.
