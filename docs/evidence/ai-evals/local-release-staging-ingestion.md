# AI artifact rubric — local release staging ingestion

Date: 2026-09-16; portability recheck: 2026-09-17. Lite. Verdict: **PASS**.

| Dimension | Result | Evidence |
|---|---|---|
| Grounding | PASS | Runtime snapshot is derived only from four named local workbooks and retains row-level typed fields, raw JSON, filenames and SHA-256 checksums. Synthetic data is test-only and never substitutes for owner data at runtime. |
| Authority | PASS | Every row is `needs_canonical_review`, staging-only, has no canonical UUID, and the report states that staged observations are not verified products or Dual RAG inputs. |
| Color honesty | PASS | All 1,763 blank colors remain `NULL`; no color is inferred from model text, variant note, URL, image or general knowledge. |
| Determinism | PASS | Same input bytes reproduce the exact snapshot, checksum, order and batch ID; stored PostgreSQL readback is byte-canonical-equivalent. |
| Transaction safety | PASS | Real PostgreSQL proves atomic rollback after a uniqueness fault, exact first insert, identical no-op and unchanged protected tables. |
| Input integrity | PASS | The exact 19-column header/count contract is enforced; regression tests reject both values and formulas in a twentieth column. |
| Rights boundary | PASS | Artifact records that access permission/republication rights were not provided and does not claim local possession permits scraping or source-file publication. |
| Auditability | PASS | Counts, checksums, batch identity, source metadata, SQL behavior and QA commands are traceable. The committed public manifest independently checks batch identity, file checksums and aggregate counts without publishing source rows. |
| Repository portability | PASS | With `HW data/` absent, 17 synthetic/artifact/repository tests pass and only 2 exact owner-data checks skip; with owner data present, all 19 focused tests pass. |

No AI-generated canonical mapping, human label, color, release identity or product claim was accepted
by this feature. The artifact is validated only as review-only staging evidence and must not be
promoted or described as verified products, evaluation truth, or Dual RAG runtime content.
