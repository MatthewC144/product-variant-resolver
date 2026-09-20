# Local release review-family knowledge projection — evidence

Date: 2026-09-19. Lite / Lean Industrial. Verdict: **PASS for private offline-evaluation documents**.

The private materialization registry
`1b8c18618390c4f224634da7a0fe3ee403c2c49f7e1614b941e4332196fc1a83` deterministically produces a
five-document projection with SHA-256
`32644f9c5b91039fde7b7a9586f8a6bf9479ea7c6878661d329ea53bed4207d8`. The documents cover 18 unique
source references. Each is typed `review_family`, remains `owner_confirmed_variants_unreviewed`, and
uses a namespace UUID that cannot be interpreted as a canonical product UUID.

Only `brand`, `casting`, and owner-confirmed `aliases` are search-eligible. Source IDs remain private
provenance and toy numbers, years, series, variant notes, candidate evidence, color, and release
attributes are absent from searchable fields. Comparison against the frozen 42-document existing
family corpus reports zero ID, UUID, or normalized brand/casting/alias collisions.

The first CLI run returned `created`, the exact second run returned `unchanged`, and `--check`
returned `valid` with the same projection checksum. Negative tests cover stale existing checksums,
registry/projection tampering, cross-corpus collisions, duplicate source assignments, conflicting or
partial outputs, public privacy, and second-write rollback.

Thirteen focused tests and all 686 repository tests pass. Ruff F/I and format, strict MyPy,
compileall, installed entry-point validation, artifact checks, privacy scan, and `git diff --check`
pass. Only the existing Starlette/AnyIO deprecation warning remains.

Runtime-indexed documents, canonical promotions, reviewed colors, PostgreSQL writes, evaluation
labels, and network requests remain zero. Existing Human Knowledge RAG files and API settings are
unchanged.
