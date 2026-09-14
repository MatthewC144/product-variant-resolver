# T49.1 — Execution consent and verification

Date:2026-09-14. Lite. Owner instruction:「請幫我執行」after the detailed T49 draft explanation.
This is interpreted narrowly as execution of the described first local-only task, not approval of
the entire future database/collection/schema/variant rollout. No separate sequential requirements,
design and tasks confirmation messages are claimed. Broader Lite G1 remains WAIT; the narrow
execution consent takes precedence only for T49.1. No subagents were requested or spawned.

The explained draft is anchored at commit `0b12b031c616ea61436f1cfa6fc3f63e202b458c`:

| Draft file | SHA256 at that commit |
|---|---|
| requirements.md | d0e9f56d4b3842c872059c642eff304988b7159cf8df6dbaaa9b74bc6d152cc6 |
| design.md | 7de64ba9250c44f530f7f16ecdbf100916731f26456defa39c9cd84a85321db9 |
| tasks.md | f774f650aab7989b132c858b389df4a359f7dbb90800201e4dc07663540ddb55 |

These hashes describe the historical draft, not an invented full G1 sign-off. Task status and
this limited exception are recorded separately. T49.2 needs an explicitly selected isolated test
database and scoped schema/import agreement before database work; no URL/volume is selected now.

## Delivered behavior (R1–R3/R14, local T49.1 scope)

`human_knowledge_snapshot.py` reads only12declared, SHA-pinned local input files: human source and
manifest, human projection and manifest, family projection and manifest, registry and manifest,
pilot staged data and manifest, final adjudicated queue and manifest. This checks this immediate
source envelope, not recursively every historical evidence document or current website rights.
The existing typed loader supplies100provisional documents plus42accepted-family documents.
IDs/UUIDs/types/all typed fields roundtrip unchanged. Raw casting/variant and family/registry entry
metadata preserve provenance, failure categories, family-only level, owner decisions and held
release references that are not fields of the typed retriever document. Source contracts are
preserved verbatim, including the old `postgresql_ingestion` exclusion; this PLAN does not lift it.

The deterministic content checksum includes sources/counts/contracts/documents/origins. The
snapshot ID is a content-addressed plan string, not a canonical identity or UUID. Validation
reconstructs the entire plan from pinned sources, so rehashing malicious edits does not grant
authenticity. Partial/duplicate/mixed/held/merge-source admissions and broadened eligibility fail.
Default API/config/runtime/retrieval/identity/final evidence and existing source data are unchanged.
No database library, SQL operation, website request, embedding build or final collector is invoked
by the new tool. A guarded-input test confirms only the12declared local sources are read.

## Publication and failure contract

The CLI publishes `reports/human-knowledge-snapshot-v1/{plan.json,report.md}` exclusively into a
new direct child of project `reports/`. Source validation precedes output directory creation.
Repetition refuses the existing directory; `--check` validates both files without writing.
Symlink sources/outputs/bundle members are rejected. Normal failures remove only newly created
owned files and the exact directory if empty; unrelated files are never recursively removed.
A process kill can leave an incomplete bundle: checking rejects it and repeating refuses it.
This is **not** a claim of crash-atomic publication or a PostgreSQL transaction/idempotent import.

## Reproduction and observed results

```sh
.venv/bin/python scripts/plan_human_knowledge_snapshot.py --check
PYTHONPATH=src .venv/bin/python -m pytest tests/test_human_knowledge_snapshot.py
PYTHONPATH=src .venv/bin/python -m pytest
.venv/bin/ruff check --select F,I src/product_variant_resolver/human_knowledge_snapshot.py scripts/plan_human_knowledge_snapshot.py tests/test_human_knowledge_snapshot.py
.venv/bin/mypy --follow-imports=skip src/product_variant_resolver/human_knowledge_snapshot.py scripts/plan_human_knowledge_snapshot.py
```

To create a genuinely new report use `--run --output "$PWD/reports/new-name"`; never replace
the committed v1 directory. This remains a local plan, not permission to import or collect.

Actual v1 generation and checker PASS.37new focused tests PASS; full suite448PASS with one
existing Starlette/AnyIOBlockingPortal deprecation warning. Focused RuffF/I and isolated strict
MyPy PASS; compilation/static Docker compose checks and stored final integrity checks PASS.
These are host/local/static results, not new container/SQL/runtime-cost/accuracy evidence.

Content SHA256: `f7830e460650e99ab5107ec0f049c96d2dcf322daa5c140c5847a53f969e144f`.
Published `plan.json` byte SHA256:
`d56391d19bf2d61acb422c05c9e9b8a21aaab81efe5c0185b0529a58d39a11a2`.
Published `report.md` byte SHA256:
`632169257646f26a7c5edba028b214b16a7b1c22058597f16af5e6a605bb242a`.
Content hash and formatted-file byte hash are intentionally different. Upstream pinned sources
and stored final output hashes remain unchanged. PostgreSQL writes0; new canonical UUIDs0;
additional real dataset rows0. The human lane remains debug-only.

Next: confirm a disposable isolated test-DB environment and bounded T49.2 schema/import scope;
no existing database reset, remote collection or default profile rollout is authorized here.
