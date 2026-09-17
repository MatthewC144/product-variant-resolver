# SEL-CRAWL1 — Lite QA review

Date:2026-09-16. Verdict:PASS for local implementation;remote canary NOT RUN.

| Requirement | Evidence and result |
|---|---|
| SC-R1–R2 | Exact host,HTTP(S),credential and permanent Fandom/Wikia guards have unit coverage. PASS. |
| SC-R3 | Local Chrome loaded a JavaScript-delayed Fandom-like table with images disabled. PASS. |
| SC-R4–R5 | Three 2025 rows retained,one 2024 row filtered,variant/color/raw/provenance preserved. PASS. |
| SC-R6 | Two-sheet XLSX exported;formulas recomputed,0 formula errors,both sheets rendered and inspected. PASS. |
| SC-R7 | One page,max5,000 rows,challenge/redirect/no-table/no-year fail paths are explicit. PASS by code/unit scope. |
| SC-R8 | Browser test used only local `file://` fixture;no target/Fandom request occurred. PASS. |

The sample workbook is synthetic and proves format only. Live compatibility,source permission and the
unknown target site's exact headers remain external checks;this review does not authorize a remote run or
promote output to PostgreSQL/canonical/Dual RAG data.

QA:6 focused tests PASS,including opt-in local Chrome and portable OpenPyXL export;full suite with the
repository's `PYTHONPATH=src`contract is615 PASS/1 browser test skipped/1 existing Starlette-AnyIO warning. Focused Ruff and strict MyPy,
compileall,Node syntax,JSON parsing,XLSX formula scan and two-sheet visual inspection PASS. Repository-wide
Ruff/MyPy still report pre-existing out-of-scope debt;no broad cleanup was performed in this feature.
