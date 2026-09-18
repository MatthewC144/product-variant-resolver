# Local release casting review batch 01 — verification evidence

Date: 2026-09-17. Lite / Lean Industrial. Gate: **packet PASS; owner decisions pending**.

The deterministic builder verified the existing source bundle and casting queue, then selected a
fixed five-question review packet covering 18 source observations. Selection consists of one
cross-source exact candidate, two normalization collisions, and two synthetic-fixture-name
candidates. All five decisions are null and `pending_owner`.

The private packet hash is
`189a3a69d6a580c6781876f79b52792617e996760cd65da379c861b1655bbb52`; its upstream queue hash is
`7961d4e6b59623277c3172e24066686e3a6ee01585fac4205a4e4f7254e0b883`. The private JSON and readable
questions remain in the gitignored local data tree. The committed manifest reveals only hashes,
selection-type counts, five questions, 18 observations, and zero decisions; it contains no casting
label, toy number, source row, or candidate ID.

Nine focused tests cover the fixed decision schema, readable semantics, repeat determinism, hold
boundary, color rejection, missing evidence, public privacy, real local aggregate, and committed
manifest. The complete repository suite passes 649/649. Changed-file Ruff F/I and format, strict
MyPy, compileall, deterministic CLI `--check`, and whitespace validation pass. The sole warning is
the pre-existing Starlette/AnyIO deprecation notice.

This milestone proves that questions were prepared faithfully, not that any answer is correct. It
does not approve a casting relationship, alias, release variant, physical color, canonical UUID,
database row, evaluation label, or Dual RAG runtime document.
